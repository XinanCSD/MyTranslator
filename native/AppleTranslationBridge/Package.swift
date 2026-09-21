// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AppleTranslationBridge",
    platforms: [.macOS(.v15)],
    products: [.executable(name: "apple-translation-bridge", targets: ["AppleTranslationBridge"])],
    targets: [.executableTarget(name: "AppleTranslationBridge")]
)
