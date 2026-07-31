import Foundation

struct PendingCheckout: Identifiable, Decodable {
    let id: Int
    let name: String
    let access_token: String
    let amount: Double
    let currency: String
    let sale_order: String
    let partner: String?
}

struct ConfigResponse: Decodable {
    let ok: Bool
    let environment: String?
    let application_id: String?
    let access_token: String?
    let location_id: String?
    let error: String?
}

struct PendingResponse: Decodable {
    let ok: Bool
    let checkouts: [PendingCheckout]?
    let error: String?
}

final class OdooAPI {
    var baseURL: String
    var apiKey: String

    init(baseURL: String, apiKey: String) {
        self.baseURL = baseURL.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        self.apiKey = apiKey
    }

    private func request(path: String, method: String = "GET", body: Data? = nil) throws -> (Data, HTTPURLResponse) {
        guard let url = URL(string: baseURL + path) else { throw URLError(.badURL) }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = body
        }
        let sem = DispatchSemaphore(value: 0)
        var resultData: Data?
        var resultResp: URLResponse?
        var resultErr: Error?
        URLSession.shared.dataTask(with: req) { data, resp, err in
            resultData = data
            resultResp = resp
            resultErr = err
            sem.signal()
        }.resume()
        sem.wait()
        if let resultErr { throw resultErr }
        guard let data = resultData, let http = resultResp as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        return (data, http)
    }

    func fetchConfig() throws -> ConfigResponse {
        let (data, http) = try request(path: "/square/reader/config")
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "Odoo", code: http.statusCode, userInfo: [
                NSLocalizedDescriptionKey: String(data: data, encoding: .utf8) ?? "config failed"
            ])
        }
        return try JSONDecoder().decode(ConfigResponse.self, from: data)
    }

    func fetchPending() throws -> [PendingCheckout] {
        let (data, http) = try request(path: "/square/reader/pending")
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "Odoo", code: http.statusCode, userInfo: [
                NSLocalizedDescriptionKey: String(data: data, encoding: .utf8) ?? "pending failed"
            ])
        }
        let decoded = try JSONDecoder().decode(PendingResponse.self, from: data)
        guard decoded.ok else { throw NSError(domain: "Odoo", code: 1, userInfo: [NSLocalizedDescriptionKey: decoded.error ?? "pending failed"]) }
        return decoded.checkouts ?? []
    }

    func complete(checkout: PendingCheckout, squarePaymentId: String) throws {
        let payload: [String: Any] = [
            "checkout_id": checkout.id,
            "access_token": checkout.access_token,
            "square_payment_id": squarePaymentId,
        ]
        let body = try JSONSerialization.data(withJSONObject: payload)
        let (data, http) = try request(path: "/square/reader/complete", method: "POST", body: body)
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "Odoo", code: http.statusCode, userInfo: [
                NSLocalizedDescriptionKey: String(data: data, encoding: .utf8) ?? "complete failed"
            ])
        }
    }
}
