import SwiftUI

/**
 Store-counter UI. After adding Square Mobile Payments SDK via SPM:
 1. Initialize SDK with SquareApplicationId from Config.plist
 2. Authorize with access_token + location_id from Odoo /square/reader/config
 3. Call PaymentManager to charge `checkout.amount`
 4. On success call api.complete(checkout:paymentId:)
 */
struct ContentView: View {
    @State private var status = "Ready"
    @State private var checkouts: [PendingCheckout] = []
    @State private var odooURL: String = ""
    @State private var apiKey: String = ""

    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 12) {
                TextField("Odoo base URL", text: $odooURL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                SecureField("Reader App API Key", text: $apiKey)
                HStack {
                    Button("Refresh pending") { refresh() }
                    Spacer()
                }
                Text(status).font(.footnote)
                List(checkouts) { item in
                    Button {
                        status = "Selected \(item.sale_order). Wire Square takePayment then complete."
                    } label: {
                        VStack(alignment: .leading) {
                            Text("\(item.sale_order) • \(item.amount) \(item.currency)")
                            Text(item.partner ?? "").font(.caption)
                        }
                    }
                }
            }
            .padding()
            .navigationTitle("Re-Ware Square")
            .onAppear(perform: loadConfig)
        }
    }

    private func loadConfig() {
        if let url = Bundle.main.url(forResource: "Config", withExtension: "plist"),
           let dict = NSDictionary(contentsOf: url) as? [String: String] {
            odooURL = dict["OdooBaseURL"] ?? ""
            apiKey = dict["OdooApiKey"] ?? ""
        }
    }

    private func refresh() {
        status = "Loading…"
        DispatchQueue.global().async {
            do {
                let api = OdooAPI(baseURL: odooURL, apiKey: apiKey)
                _ = try api.fetchConfig()
                let rows = try api.fetchPending()
                DispatchQueue.main.async {
                    checkouts = rows
                    status = "Pending: \(rows.count)"
                }
            } catch {
                DispatchQueue.main.async {
                    status = "Error: \(error.localizedDescription)"
                }
            }
        }
    }
}
