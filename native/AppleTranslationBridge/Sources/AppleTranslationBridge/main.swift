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
        Color.clear
            .frame(width: 1, height: 1)
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
    static func main() {
        do {
            let data = FileHandle.standardInput.readDataToEndOfFile()
            let request = try JSONDecoder().decode(Request.self, from: data)
            run(request)
        } catch {
            writeAndExit(
                Response(
                    ok: false,
                    translation: nil,
                    error: String(describing: error)
                ),
                status: 1
            )
        }
    }

    @MainActor
    private static func run(_ request: Request) {
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)

        var finished = false

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1, height: 1),
            styleMask: [],
            backing: .buffered,
            defer: false
        )
        window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(
            rootView: BridgeView(request: request) { response in
                guard !finished else { return }
                finished = true
                writeAndExit(response, status: response.ok ? 0 : 1)
            }
        )
        window.orderOut(nil)

        app.run()
    }

    @MainActor
    private static func writeAndExit(_ response: Response, status: Int32) {
        if let output = try? JSONEncoder().encode(response) {
            FileHandle.standardOutput.write(output)
            FileHandle.standardOutput.write(Data([10]))
        }

        if status == 0 {
            NSApplication.shared.terminate(nil)
        } else {
            Foundation.exit(status)
        }
    }
}
