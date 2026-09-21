import AppKit
import Foundation
import SwiftUI
import Translation

struct Request: Decodable {
    let source: String
    let target: String
    let text: String
}

struct Response: Encodable {
    let ok: Bool
    let translation: String?
    let error: String?
}

struct BridgeView: View {
    let request: Request
    let completion: (Response) -> Void

    @State private var configuration: TranslationSession.Configuration?

    init(request: Request, completion: @escaping (Response) -> Void) {
        self.request = request
        self.completion = completion
        _configuration = State(
            initialValue: TranslationSession.Configuration(
                source: Locale.Language(identifier: request.source),
                target: Locale.Language(identifier: request.target)
            )
        )
    }

    var body: some View {
        Text("Translating…")
            .frame(width: 240, height: 80)
            .translationTask(configuration) { session in
                Task { @MainActor in
                    do {
                        let response = try await session.translate(request.text)
                        completion(
                            Response(
                                ok: true,
                                translation: response.targetText,
                                error: nil
                            )
                        )
                    } catch {
                        completion(
                            Response(
                                ok: false,
                                translation: nil,
                                error: String(describing: error)
                            )
                        )
                    }
                }
            }
    }
}

@main
struct AppleTranslationBridge {
    @MainActor
    static func main() {
        do {
            let data = FileHandle.standardInput.readDataToEndOfFile()
            let request = try JSONDecoder().decode(Request.self, from: data)
            run(request)
        } catch {
            writeResponse(
                Response(
                    ok: false,
                    translation: nil,
                    error: String(describing: error)
                )
            )
            Foundation.exit(1)
        }
    }

    @MainActor
    private static func run(_ request: Request) {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        app.activate(ignoringOtherApps: true)

        var finished = false

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 240, height: 80),
            styleMask: [.titled],
            backing: .buffered,
            defer: false
        )
        window.title = "MyTranslator"
        window.isReleasedWhenClosed = false
        window.center()
        window.contentView = NSHostingView(
            rootView: BridgeView(request: request) { response in
                guard !finished else { return }
                finished = true
                writeResponse(response)
                app.terminate(nil)
            }
        )

        window.makeKeyAndOrderFront(nil)
        app.run()
    }

    private static func writeResponse(_ response: Response) {
        guard let output = try? JSONEncoder().encode(response) else {
            return
        }
        FileHandle.standardOutput.write(output)
        FileHandle.standardOutput.write(Data([10]))
    }
}
