// Measure approved references and orthographic mesh renders locally.
import Foundation
import Vision
import ImageIO

guard CommandLine.arguments.count == 3 else {
    fatalError("Usage: inspect-face-landmarks <image> <json-output>")
}
let input = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2])
guard let decoder = CGImageSourceCreateWithURL(input as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(decoder, 0, nil) else {
    fatalError("Cannot decode image")
}
let request = VNDetectFaceLandmarksRequest()
try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
guard let face = request.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width }),
      let landmarks = face.landmarks else { fatalError("No face landmarks") }
let box = face.boundingBox
let regions: [(String, VNFaceLandmarkRegion2D?)] = [
    ("contour", landmarks.faceContour), ("leftEye", landmarks.leftEye),
    ("rightEye", landmarks.rightEye), ("leftEyebrow", landmarks.leftEyebrow),
    ("rightEyebrow", landmarks.rightEyebrow), ("nose", landmarks.nose),
    ("noseCrest", landmarks.noseCrest), ("medianLine", landmarks.medianLine),
    ("outerLips", landmarks.outerLips), ("innerLips", landmarks.innerLips),
    ("leftPupil", landmarks.leftPupil), ("rightPupil", landmarks.rightPupil)
]
var points: [String: [[Double]]] = [:]
for (name, region) in regions {
    guard let region else { continue }
    points[name] = region.normalizedPoints.map { point in
        [Double(box.minX + CGFloat(point.x) * box.width),
         Double(1 - box.minY - CGFloat(point.y) * box.height)]
    }
}
let report: [String: Any] = ["source": input.path, "width": image.width, "height": image.height,
    "coordinates": "normalized image coordinates, origin top left", "confidence": face.confidence,
    "points": points]
try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: output)
print("Measured \(points.values.reduce(0) { $0 + $1.count }) points in \(input.lastPathComponent)")
