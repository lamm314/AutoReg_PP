import SwiftUI
import Foundation
import AppKit

struct SheetRow: Identifiable {
    let id = UUID()
    let sheetRow: String
    let b: String
    let c: String
    let d: String
    let e: String
    let i: String
    let j: String
    let k: String
}

struct AppConfig: Codable {
    var sheetURL: String = ""
    var proxyKey: String = ""
}

struct ServiceAccountCredentials: Decodable {
    let type: String
    let projectID: String
    let privateKey: String
    let clientEmail: String
    let tokenURI: String

    enum CodingKeys: String, CodingKey {
        case type
        case projectID = "project_id"
        case privateKey = "private_key"
        case clientEmail = "client_email"
        case tokenURI = "token_uri"
    }
}

struct GoogleAccessTokenResponse: Decodable {
    let accessToken: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
    }
}

struct GoogleValuesResponse: Decodable {
    let values: [[String]]?
}

enum RowStatusOption: String, CaseIterable, Identifiable {
    case live = "LIVE"
    case upID = "UP ID"

    var id: String { rawValue }
}

enum AppError: LocalizedError {
    case invalidSheetURL
    case missingSheetURL
    case missingProxyKey
    case invalidProxyResponse
    case invalidSheetResponse(Int)
    case serviceAccountNotFound
    case invalidServiceAccountFile
    case tokenRequestFailed(Int)
    case googleSheetsUpdateFailed(Int)
    case signingFailed

    var errorDescription: String? {
        switch self {
        case .invalidSheetURL:
            return "Google Sheet URL khong hop le."
        case .missingSheetURL:
            return "Ban chua nhap Google Sheet URL."
        case .missingProxyKey:
            return "Ban chua nhap Proxy API key."
        case .invalidProxyResponse:
            return "Phan hoi proxy khong hop le."
        case .invalidSheetResponse(let code):
            return "Khong doc duoc Google Sheet. HTTP \(code)"
        case .serviceAccountNotFound:
            return "Khong tim thay file service account JSON trong thu muc du an."
        case .invalidServiceAccountFile:
            return "File service account JSON khong hop le."
        case .tokenRequestFailed(let code):
            return "Khong lay duoc Google access token. HTTP \(code)"
        case .googleSheetsUpdateFailed(let code):
            return "Google Sheets API tra ve loi. HTTP \(code)"
        case .signingFailed:
            return "Khong ky duoc JWT bang private key cua service account."
        }
    }
}

@MainActor
final class AppViewModel: ObservableObject {
    @Published var sheetURL: String = ""
    @Published var proxyKey: String = ""
    @Published var statusText: String = "San sang."
    @Published var proxyStatusText: String = "Chua doi proxy."
    @Published var summaryText: String = "Chua tai du lieu"
    @Published var copyStatusText: String = "Bam vao o du lieu de copy."
    @Published var rowActionStatusText: String = "Chon trang thai va nhap so dien thoai de ghi vao cot L/M."
    @Published var rows: [SheetRow] = []
    @Published var isLoadingRows = false
    @Published var isChangingProxy = false
    @Published var isUpdatingSheet = false

    private let sheetName = "people"
    private let resultLimit = 20
    private let configURL: URL
    private let baseURL: URL

    init() {
        let baseURL = Self.resolveBaseDirectory()
        self.baseURL = baseURL
        self.configURL = baseURL.appendingPathComponent("app_config.json")
        loadConfig()
    }

    private static func resolveBaseDirectory() -> URL {
        let fileManager = FileManager.default
        let currentDirectory = URL(fileURLWithPath: fileManager.currentDirectoryPath)
        let bundleURL = Bundle.main.bundleURL

        if bundleURL.pathExtension == "app" {
            return bundleURL.deletingLastPathComponent()
        }

        let executableURL = Bundle.main.executableURL ?? currentDirectory
        let executableDirectory = executableURL.deletingLastPathComponent()

        if executableDirectory.lastPathComponent == "MacOS" {
            return executableDirectory
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
        }

        return currentDirectory
    }

    func loadConfig() {
        guard let data = try? Data(contentsOf: configURL) else { return }
        guard let config = try? JSONDecoder().decode(AppConfig.self, from: data) else { return }
        sheetURL = config.sheetURL
        proxyKey = config.proxyKey
    }

    func saveConfig() {
        let config = AppConfig(sheetURL: sheetURL.trimmingCharacters(in: .whitespacesAndNewlines),
                               proxyKey: proxyKey.trimmingCharacters(in: .whitespacesAndNewlines))
        do {
            let data = try JSONEncoder.pretty.encode(config)
            try data.write(to: configURL, options: .atomic)
            statusText = "Da luu cau hinh vao app_config.json."
        } catch {
            statusText = "Khong the luu cau hinh: \(error.localizedDescription)"
        }
    }

    func fetchRows() {
        saveConfig()
        let currentURL = sheetURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !currentURL.isEmpty else {
            statusText = AppError.missingSheetURL.localizedDescription
            return
        }

        isLoadingRows = true
        statusText = "Dang doc sheet..."

        Task {
            do {
                let fetchedRows = try await fetchSheetRows(sheetURL: currentURL)
                rows = fetchedRows
                summaryText = "\(fetchedRows.count)/\(resultLimit) dong"
                statusText = "Da lay \(fetchedRows.count) dong tu sheet '\(sheetName)' co cot L trong."
                copyStatusText = fetchedRows.isEmpty ? "Khong co du lieu de copy." : "Bam vao o du lieu de copy."
                rowActionStatusText = fetchedRows.isEmpty ? "Khong co dong nao de cap nhat." : "Chon trang thai va nhap so dien thoai de ghi vao cot L/M."
            } catch {
                rows = []
                summaryText = "Khong tai du lieu"
                statusText = error.localizedDescription
                copyStatusText = "Bam vao o du lieu de copy."
                rowActionStatusText = "Khong co dong nao de cap nhat."
            }
            isLoadingRows = false
        }
    }

    func changeProxy() {
        saveConfig()
        let currentKey = proxyKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !currentKey.isEmpty else {
            proxyStatusText = AppError.missingProxyKey.localizedDescription
            return
        }

        isChangingProxy = true
        proxyStatusText = "Dang doi proxy..."

        Task {
            do {
                proxyStatusText = try await requestProxyChange(apiKey: currentKey)
            } catch {
                proxyStatusText = error.localizedDescription
            }
            isChangingProxy = false
        }
    }

    private func fetchSheetRows(sheetURL: String) async throws -> [SheetRow] {
        do {
            let values = try await fetchSheetRowsUsingServiceAccount(sheetURL: sheetURL)
            return pickEmptyLRows(values)
        } catch AppError.serviceAccountNotFound {
            let csvURL = try buildCSVURL(from: sheetURL)
            var request = URLRequest(url: csvURL)
            request.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")

            let (data, response) = try await URLSession.shared.data(for: request)
            if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
                throw AppError.invalidSheetResponse(http.statusCode)
            }

            guard let payload = String(data: data, encoding: .utf8) else {
                throw AppError.invalidSheetResponse(-1)
            }

            let rows = parseCSV(payload.replacingOccurrences(of: "\u{feff}", with: ""))
            return pickEmptyLRows(rows)
        }
    }

    private func requestProxyChange(apiKey: String) async throws -> String {
        guard !apiKey.isEmpty else { throw AppError.missingProxyKey }
        let encodedKey = apiKey.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? apiKey
        guard let url = URL(string: "https://app.proxyno1.com/api/change-key-ip/\(encodedKey)") else {
            throw AppError.invalidProxyResponse
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, _) = try await URLSession.shared.data(for: request)
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw AppError.invalidProxyResponse
        }

        let status = object["status"] as? Int ?? -1
        let message = object["message"] as? String ?? "Khong co message"
        if status == 0 {
            try await Task.sleep(nanoseconds: 5_000_000_000)
            return "status=0 | \(message) | Da doi proxy, nen cho on dinh them 5-10 giay."
        }
        return "status=\(status) | \(message)"
    }

    private func buildCSVURL(from sheetURL: String) throws -> URL {
        let marker = "/d/"
        guard let markerRange = sheetURL.range(of: marker) else {
            throw AppError.invalidSheetURL
        }
        let tail = sheetURL[markerRange.upperBound...]
        let spreadsheetID = tail.split(separator: "/").first.map(String.init) ?? ""
        guard !spreadsheetID.isEmpty else { throw AppError.invalidSheetURL }

        var components = URLComponents()
        components.scheme = "https"
        components.host = "docs.google.com"
        components.path = "/spreadsheets/d/\(spreadsheetID)/gviz/tq"
        components.queryItems = [
            URLQueryItem(name: "tqx", value: "out:csv"),
            URLQueryItem(name: "sheet", value: sheetName),
        ]

        guard let url = components.url else { throw AppError.invalidSheetURL }
        return url
    }

    private func pickEmptyLRows(_ rows: [[String]]) -> [SheetRow] {
        var selected: [SheetRow] = []

        for (index, rawRow) in rows.enumerated() {
            var row = rawRow
            while row.count <= 11 {
                row.append("")
            }

            if row.allSatisfy({ $0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) {
                continue
            }
            if index == 0 {
                continue
            }
            if !row[11].trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                continue
            }

            selected.append(
                SheetRow(
                    sheetRow: String(index + 1),
                    b: row[1].trimmed,
                    c: row[2].trimmed,
                    d: row[3].trimmed,
                    e: row[4].trimmed,
                    i: row[8].trimmed,
                    j: row[9].trimmed,
                    k: row[10].trimmed
                )
            )

            if selected.count >= resultLimit {
                break
            }
        }

        return selected
    }

    private func parseCSV(_ text: String) -> [[String]] {
        var rows: [[String]] = []
        var row: [String] = []
        var field = ""
        var insideQuotes = false

        let characters = Array(text)
        var index = 0

        while index < characters.count {
            let char = characters[index]

            if insideQuotes {
                if char == "\"" {
                    let nextIndex = index + 1
                    if nextIndex < characters.count, characters[nextIndex] == "\"" {
                        field.append("\"")
                        index += 1
                    } else {
                        insideQuotes = false
                    }
                } else {
                    field.append(char)
                }
            } else {
                switch char {
                case "\"":
                    insideQuotes = true
                case ",":
                    row.append(field)
                    field = ""
                case "\n":
                    row.append(field)
                    rows.append(row)
                    row = []
                    field = ""
                case "\r":
                    break
                default:
                    field.append(char)
                }
            }

            index += 1
        }

        if !field.isEmpty || !row.isEmpty {
            row.append(field)
            rows.append(row)
        }

        return rows
    }

    func copyValue(_ value: String, column: String, row: String) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(value, forType: .string)
        copyStatusText = "Da copy \(column)\(row): \(value.isEmpty ? "-" : value)"
    }

    func updateRowStatus(row: SheetRow, status: RowStatusOption, phoneNumber: String) {
        let cleanedPhone = phoneNumber.trimmed
        guard !cleanedPhone.isEmpty else {
            rowActionStatusText = "Ban chua nhap so dien thoai de ghi vao M\(row.sheetRow)."
            return
        }

        isUpdatingSheet = true

        Task {
            do {
                try await updateGoogleSheetRow(
                    rowNumber: row.sheetRow,
                    status: status.rawValue,
                    phoneNumber: cleanedPhone
                )
                rowActionStatusText = "Da ghi thanh cong: L\(row.sheetRow) = \(status.rawValue), M\(row.sheetRow) = \(cleanedPhone)"
            } catch {
                rowActionStatusText = error.localizedDescription
            }
            isUpdatingSheet = false
        }
    }

    private func fetchSheetRowsUsingServiceAccount(sheetURL: String) async throws -> [[String]] {
        let credentials = try loadServiceAccountCredentials()
        let accessToken = try await fetchGoogleAccessToken(credentials: credentials)
        let spreadsheetID = try extractSpreadsheetID(from: sheetURL)
        let range = "\(sheetName)!A:M".addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? "\(sheetName)!A:M"
        guard let url = URL(string: "https://sheets.googleapis.com/v4/spreadsheets/\(spreadsheetID)/values/\(range)") else {
            throw AppError.invalidSheetURL
        }

        var request = URLRequest(url: url)
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")

        let (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            throw AppError.invalidSheetResponse(http.statusCode)
        }

        let payload = try JSONDecoder().decode(GoogleValuesResponse.self, from: data)
        return payload.values ?? []
    }

    private func updateGoogleSheetRow(rowNumber: String, status: String, phoneNumber: String) async throws {
        let sheetURL = sheetURL.trimmed
        let credentials = try loadServiceAccountCredentials()
        let accessToken = try await fetchGoogleAccessToken(credentials: credentials)
        let spreadsheetID = try extractSpreadsheetID(from: sheetURL)

        guard let url = URL(string: "https://sheets.googleapis.com/v4/spreadsheets/\(spreadsheetID)/values:batchUpdate") else {
            throw AppError.invalidSheetURL
        }

        let body: [String: Any] = [
            "valueInputOption": "RAW",
            "data": [
                ["range": "\(sheetName)!L\(rowNumber)", "values": [[status]]],
                ["range": "\(sheetName)!M\(rowNumber)", "values": [[phoneNumber]]],
            ],
        ]

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            throw AppError.googleSheetsUpdateFailed(http.statusCode)
        }
    }

    private func loadServiceAccountCredentials() throws -> ServiceAccountCredentials {
        let fileManager = FileManager.default
        let searchDirectories = [
            baseURL,
            URL(fileURLWithPath: fileManager.currentDirectoryPath),
        ]

        let jsonURL = searchDirectories
            .compactMap { directory in
                try? fileManager.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            }
            .flatMap { $0 }
            .first(where: {
                $0.pathExtension.lowercased() == "json" &&
                $0.lastPathComponent != "app_config.json" &&
                $0.lastPathComponent.contains("carbide-booth")
            })

        guard let jsonURL else {
            throw AppError.serviceAccountNotFound
        }

        let data = try Data(contentsOf: jsonURL)
        let credentials = try JSONDecoder().decode(ServiceAccountCredentials.self, from: data)
        guard credentials.type == "service_account" else {
            throw AppError.invalidServiceAccountFile
        }
        return credentials
    }

    private func fetchGoogleAccessToken(credentials: ServiceAccountCredentials) async throws -> String {
        let jwt = try makeServiceAccountJWT(credentials: credentials)
        guard let url = URL(string: credentials.tokenURI) else {
            throw AppError.invalidServiceAccountFile
        }

        let form = [
            "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer",
            "assertion=\(jwt.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? jwt)",
        ].joined(separator: "&")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = form.data(using: .utf8)

        let (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            throw AppError.tokenRequestFailed(http.statusCode)
        }

        let tokenResponse = try JSONDecoder().decode(GoogleAccessTokenResponse.self, from: data)
        return tokenResponse.accessToken
    }

    private func makeServiceAccountJWT(credentials: ServiceAccountCredentials) throws -> String {
        let header = ["alg": "RS256", "typ": "JWT"]
        let now = Int(Date().timeIntervalSince1970)
        let payload: [String: Any] = [
            "iss": credentials.clientEmail,
            "scope": "https://www.googleapis.com/auth/spreadsheets",
            "aud": credentials.tokenURI,
            "iat": now,
            "exp": now + 3600,
        ]

        let headerData = try JSONSerialization.data(withJSONObject: header)
        let payloadData = try JSONSerialization.data(withJSONObject: payload)
        let headerPart = headerData.base64URLEncodedString()
        let payloadPart = payloadData.base64URLEncodedString()
        let signingInput = "\(headerPart).\(payloadPart)"
        let signature = try signJWT(signingInput, privateKeyPEM: credentials.privateKey)
        return "\(signingInput).\(signature)"
    }

    private func signJWT(_ message: String, privateKeyPEM: String) throws -> String {
        let tempDirectory = FileManager.default.temporaryDirectory
        let keyURL = tempDirectory.appendingPathComponent(UUID().uuidString + ".pem")
        let messageURL = tempDirectory.appendingPathComponent(UUID().uuidString + ".txt")
        defer {
            try? FileManager.default.removeItem(at: keyURL)
            try? FileManager.default.removeItem(at: messageURL)
        }

        do {
            try privateKeyPEM.write(to: keyURL, atomically: true, encoding: .utf8)
            try message.write(to: messageURL, atomically: true, encoding: .utf8)

            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            process.arguments = [
                "openssl",
                "dgst",
                "-sha256",
                "-sign",
                keyURL.path,
                "-binary",
                messageURL.path,
            ]

            let outputPipe = Pipe()
            let errorPipe = Pipe()
            process.standardOutput = outputPipe
            process.standardError = errorPipe

            try process.run()
            process.waitUntilExit()

            guard process.terminationStatus == 0 else {
                throw AppError.signingFailed
            }

            let signature = outputPipe.fileHandleForReading.readDataToEndOfFile()
            guard !signature.isEmpty else {
                throw AppError.signingFailed
            }

            return signature.base64URLEncodedString()
        } catch {
            throw AppError.signingFailed
        }
    }

    private func extractSpreadsheetID(from sheetURL: String) throws -> String {
        let marker = "/d/"
        guard let markerRange = sheetURL.range(of: marker) else {
            throw AppError.invalidSheetURL
        }
        let tail = sheetURL[markerRange.upperBound...]
        let spreadsheetID = tail.split(separator: "/").first.map(String.init) ?? ""
        guard !spreadsheetID.isEmpty else {
            throw AppError.invalidSheetURL
        }
        return spreadsheetID
    }
}

struct ContentView: View {
    @StateObject private var viewModel = AppViewModel()
    @State private var selectedRowID: SheetRow.ID?
    @State private var selectedStatus: RowStatusOption = .live
    @State private var phoneNumber: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Sheet + Proxy Tool")
                .font(.title.bold())

            configSection
            statusSection
            resultSection
        }
        .padding(20)
        .frame(minWidth: 980, minHeight: 720, alignment: .topLeading)
        .onChange(of: viewModel.rows.count) { _, _ in
            if let first = viewModel.rows.first {
                selectedRowID = first.id
            } else {
                selectedRowID = nil
            }
        }
    }

    private var selectedRow: SheetRow? {
        guard let selectedRowID else { return nil }
        return viewModel.rows.first { $0.id == selectedRowID }
    }

    private var configSection: some View {
        GroupBox("Cau hinh") {
            VStack(alignment: .leading, spacing: 12) {
                Text("Nhap link Google Sheet va Proxy API key. App luu du lieu vao app_config.json.")
                    .foregroundStyle(.secondary)

                HStack {
                    Text("Google Sheet URL")
                        .frame(width: 130, alignment: .leading)
                    TextField("https://docs.google.com/spreadsheets/d/...", text: $viewModel.sheetURL)
                        .textFieldStyle(.roundedBorder)
                }

                HStack {
                    Text("Proxy API key")
                        .frame(width: 130, alignment: .leading)
                    TextField("TEST0123456789", text: $viewModel.proxyKey)
                        .textFieldStyle(.roundedBorder)
                }

                HStack(spacing: 12) {
                    Button("Luu cau hinh") {
                        viewModel.saveConfig()
                    }

                    Button(viewModel.isLoadingRows ? "Dang tai..." : "Lay 20 dong") {
                        viewModel.fetchRows()
                    }
                    .disabled(viewModel.isLoadingRows)

                    Button(viewModel.isChangingProxy ? "Dang doi..." : "Doi proxy") {
                        viewModel.changeProxy()
                    }
                    .disabled(viewModel.isChangingProxy)
                }
            }
        }
    }

    private var statusSection: some View {
        GroupBox("Trang thai") {
            VStack(alignment: .leading, spacing: 8) {
                Text("So dong: \(viewModel.summaryText)")
                Text("Doc sheet: \(viewModel.statusText)")
                Text("Proxy: \(viewModel.proxyStatusText)")
                Text("Copy: \(viewModel.copyStatusText)")
                Text("Cap nhat L/M: \(viewModel.rowActionStatusText)")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var resultSection: some View {
        GroupBox("Ket qua 20 dong dau tien") {
            VStack(alignment: .leading, spacing: 10) {
                Text("Chon 1 dong ben trai, sau do bam vao tung truong ben phai de copy.")
                    .foregroundStyle(.secondary)

                HStack(alignment: .top, spacing: 16) {
                    rowListSection
                    detailSection
                }
            }
            .frame(minHeight: 360)
        }
    }

    private var rowListSection: some View {
        GroupBox("Danh sach dong") {
            if viewModel.rows.isEmpty {
                Text("Chua co du lieu")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
                    .padding()
            } else {
                List(viewModel.rows, selection: $selectedRowID) { row in
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Row \(row.sheetRow)  •  \(row.c)")
                            .font(.system(size: 13, weight: .semibold))
                        Text(row.i.isEmpty ? row.e : row.i)
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    .padding(.vertical, 4)
                    .tag(row.id)
                }
                .listStyle(.inset)
            }
        }
        .frame(width: 320)
        .frame(minHeight: 380)
    }

    private var detailSection: some View {
        GroupBox("Chi tiet dong duoc chon") {
            if let row = selectedRow {
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        detailHeader(row)
                        detailGrid(row)
                        actionSection(row)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 4)
                }
            } else {
                Text("Chon mot dong o ben trai de xem va copy nhanh.")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
                    .padding()
            }
        }
        .frame(maxWidth: .infinity, minHeight: 380)
    }

    private func detailHeader(_ row: SheetRow) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Row \(row.sheetRow)")
                .font(.system(size: 20, weight: .bold))
            Text(row.c.isEmpty ? "Khong co ten" : row.c)
                .font(.system(size: 14))
                .foregroundStyle(.secondary)
        }
    }

    private func detailGrid(_ row: SheetRow) -> some View {
        LazyVGrid(
            columns: [
                GridItem(.flexible(), spacing: 12),
                GridItem(.flexible(), spacing: 12),
            ],
            spacing: 12
        ) {
            copyCard(title: "B", value: row.b, rowNumber: row.sheetRow)
            copyCard(title: "C", value: row.c, rowNumber: row.sheetRow)
            copyCard(title: "D", value: row.d, rowNumber: row.sheetRow)
            copyCard(title: "E", value: row.e, rowNumber: row.sheetRow)
            copyCard(title: "I", value: row.i, rowNumber: row.sheetRow)
            copyCard(title: "J", value: row.j, rowNumber: row.sheetRow)
            copyCard(title: "K", value: row.k, rowNumber: row.sheetRow)
        }
    }

    private func copyCard(title: String, value: String, rowNumber: String) -> some View {
        Button {
            viewModel.copyValue(value, column: title, row: rowNumber)
        } label: {
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(.secondary)
                Text(value.isEmpty ? "-" : value)
                    .font(.system(size: 14, weight: .medium))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .multilineTextAlignment(.leading)
                    .lineLimit(4)
                    .fixedSize(horizontal: false, vertical: true)
                Text("Bam de copy")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, minHeight: 92, alignment: .topLeading)
            .padding(12)
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
        .buttonStyle(.plain)
        .help("Bam de copy")
    }

    private func actionSection(_ row: SheetRow) -> some View {
        GroupBox("Cap nhat trang thai cua dong nay") {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 12) {
                    Text("Trang thai")
                        .frame(width: 90, alignment: .leading)
                    Picker("Trang thai", selection: $selectedStatus) {
                        ForEach(RowStatusOption.allCases) { option in
                            Text(option.rawValue).tag(option)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                HStack(spacing: 12) {
                    Text("So dien thoai")
                        .frame(width: 90, alignment: .leading)
                    TextField("Nhap so dien thoai de ghi vao cot M", text: $phoneNumber)
                        .textFieldStyle(.roundedBorder)
                }

                HStack(spacing: 12) {
                    Text("Se ghi")
                        .frame(width: 90, alignment: .leading)
                    VStack(alignment: .leading, spacing: 4) {
                        Text("L\(row.sheetRow) = \(selectedStatus.rawValue)")
                        Text("M\(row.sheetRow) = \(phoneNumber.isEmpty ? "(chua nhap)" : phoneNumber)")
                            .foregroundStyle(.secondary)
                    }
                }

                Button(viewModel.isUpdatingSheet ? "Dang cap nhat..." : "Xac nhan va ghi vao sheet") {
                    viewModel.updateRowStatus(row: row, status: selectedStatus, phoneNumber: phoneNumber)
                }
                .disabled(viewModel.isUpdatingSheet)
            }
        }
    }
}

extension JSONEncoder {
    static var pretty: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return encoder
    }
}

extension String {
    var trimmed: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

extension Data {
    func base64URLEncodedString() -> String {
        base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

@main
struct SheetProxyNativeApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowResizability(.contentSize)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }
}
