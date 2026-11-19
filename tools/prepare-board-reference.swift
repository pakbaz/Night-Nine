// Local model conditioning from an approved board. Preserve the selected source pixels.
import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers
import CryptoKit

guard CommandLine.arguments.count == 7 else {
    fatalError("Usage: prepare-board-reference <board.png> <conditioning.png> <x> <y> <width> <height>")
}
let source = URL(fileURLWithPath: CommandLine.arguments[1])
let target = URL(fileURLWithPath: CommandLine.arguments[2])
let numbers = CommandLine.arguments[3...6].map { Double($0)! }
let crop = CGRect(x: numbers[0], y: numbers[1], width: numbers[2], height: numbers[3])
guard !FileManager.default.fileExists(atPath: target.path),
      let decoder = CGImageSourceCreateWithURL(source as CFURL, nil),
      let board = CGImageSourceCreateImageAtIndex(decoder, 0, nil),
      CGRect(x: 0, y: 0, width: board.width, height: board.height).contains(crop),
      let input = board.cropping(to: crop) else { fatalError("Existing output or invalid source/crop") }
let handler = VNImageRequestHandler(cgImage: input, options: [:])
let request = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([request])
guard let observation = request.results?.first, !observation.allInstances.isEmpty else {
    fatalError("No foreground instance detected")
}
// Choose the largest complete figure; ignore smaller portrait insets and typography.
let labels = observation.instanceMask
CVPixelBufferLockBaseAddress(labels, .readOnly)
let width = CVPixelBufferGetWidth(labels)
let height = CVPixelBufferGetHeight(labels)
let stride = CVPixelBufferGetBytesPerRow(labels)
let bytes = CVPixelBufferGetBaseAddress(labels)!.assumingMemoryBound(to: UInt8.self)
var counts = [Int: Int]()
for y in 0..<height {
    for x in 0..<width {
        let instance = Int(bytes[y * stride + x])
        if observation.allInstances.contains(instance) { counts[instance, default: 0] += 1 }
    }
}
CVPixelBufferUnlockBaseAddress(labels, .readOnly)
guard let chosen = counts.max(by: { $0.value < $1.value })?.key else { fatalError("Empty instance mask") }
let pixels = try observation.generateScaledMaskForImage(forInstances: IndexSet(integer: chosen), from: handler)
let foreground = CIImage(cgImage: input)
let result = foreground.applyingFilter("CIBlendWithMask", parameters: [
    kCIInputBackgroundImageKey: CIImage(color: CIColor.clear).cropped(to: foreground.extent),
    kCIInputMaskImageKey: CIImage(cvPixelBuffer: pixels)
])
let context = CIContext(options: [.cacheIntermediates: false])
guard let output = context.createCGImage(result, from: foreground.extent),
      let writer = CGImageDestinationCreateWithURL(target as CFURL, UTType.png.identifier as CFString, 1, nil) else {
    fatalError("Cannot encode conditioning image")
}
CGImageDestinationAddImage(writer, output, nil)
guard CGImageDestinationFinalize(writer) else { fatalError("PNG write failed") }
func hash(_ url: URL) throws -> String {
    SHA256.hash(data: try Data(contentsOf: url)).map { String(format: "%02x", $0) }.joined()
}
let record: [String: Any] = [
    "source": source.path, "source_sha256": try hash(source), "crop_xywh": numbers,
    "operation": "Approved-board crop and largest Apple Vision foreground mask; original RGB preserved.",
    "mask_instances": Dictionary(uniqueKeysWithValues: counts.map { (String($0.key), $0.value) }),
    "selected_instance": chosen, "output_sha256": try hash(target),
    "reference_image_uploads": false, "cloud_credits": 0
]
try JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys]).write(to: target.deletingPathExtension().appendingPathExtension("json"))
print("Prepared \(input.width)x\(input.height) local conditioning; selected foreground \(chosen)")
