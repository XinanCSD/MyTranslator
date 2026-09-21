import Foundation
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

func run(_ request: Request) async -> Response {
    do {
        let session = try await TranslationSession(
            installedSource: Locale.Language(identifier: request.source),
            target: Locale.Language(identifier: request.target)
        )
        let response = try await session.translate(request.text)
        return Response(ok: true, translation: response.targetText, error: nil)
    } catch {
        return Response(ok: false, translation: nil, error: String(describing: error))
    }
}

@main
struct AppleTranslationBridge {
    static func main() async {
        do {
            let data = FileHandle.standardInput.readDataToEndOfFile()
            let request = try JSONDecoder().decode(Request.self, from: data)
            let response = await run(request)
            let output = try JSONEncoder().encode(response)
            FileHandle.standardOutput.write(output)
            FileHandle.standardOutput.write(Data([10]))
        } catch {
            let response = Response(ok: false, translation: nil, error: String(describing: error))
            if let output = try? JSONEncoder().encode(response) {
                FileHandle.standardOutput.write(output)
                FileHandle.standardOutput.write(Data([10]))
            }
            Foundation.exit(1)
        }
    }
}
