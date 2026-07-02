import Foundation
import Vision
import CoreGraphics
import ImageIO
import CoreImage

struct FaceResult: Codable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
    let confidence: Float
    let kind: String
    let imageWidth: Int
    let imageHeight: Int
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(1)
}

guard CommandLine.arguments.count >= 2 else {
    fail("usage: FaceDetect image-path")
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
guard let source = CGImageSourceCreateWithURL(imageURL as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    fail("could not load image")
}

func convert(_ obs: VNDetectedObjectObservation, image: CGImage, kind: String) -> FaceResult {
    let box = obs.boundingBox
    let imageWidth = image.width
    let imageHeight = image.height
    let x = box.minX * Double(imageWidth)
    let y = (1.0 - box.maxY) * Double(imageHeight)
    let width = box.width * Double(imageWidth)
    let height = box.height * Double(imageHeight)
    return FaceResult(
        x: x,
        y: y,
        width: width,
        height: height,
        confidence: obs.confidence,
        kind: kind,
        imageWidth: imageWidth,
        imageHeight: imageHeight
    )
}

func skinFallback(image: CGImage) -> FaceResult? {
    let width = image.width
    let height = image.height
    let bytesPerPixel = 4
    let bytesPerRow = bytesPerPixel * width
    var pixels = [UInt8](repeating: 0, count: height * bytesPerRow)
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    guard let context = CGContext(
        data: &pixels,
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: bytesPerRow,
        space: colorSpace,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else {
        return nil
    }
    context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))

    var count = 0.0
    var sumX = 0.0
    var sumY = 0.0
    var minX = Double(width)
    var minY = Double(height)
    var maxX = 0.0
    var maxY = 0.0

    for y in stride(from: Int(Double(height) * 0.08), to: Int(Double(height) * 0.92), by: 3) {
        for x in stride(from: 0, to: width, by: 3) {
            let i = y * bytesPerRow + x * bytesPerPixel
            let rA = Double(pixels[i])
            let gA = Double(pixels[i + 1])
            let bA = Double(pixels[i + 2])
            let rB = Double(pixels[i + 2])
            let gB = Double(pixels[i + 1])
            let bB = Double(pixels[i])
            let maxA = max(rA, max(gA, bA))
            let minA = min(rA, min(gA, bA))
            let maxB = max(rB, max(gB, bB))
            let minB = min(rB, min(gB, bB))
            let isSkinA = rA > 55 && gA > 32 && bA > 20 && rA > bA * 1.08 && maxA - minA > 8
            let isSkinB = rB > 55 && gB > 32 && bB > 20 && rB > bB * 1.08 && maxB - minB > 8
            let isSkin = isSkinA || isSkinB
            if isSkin {
                let weight = min(3.0, max(1.0, (maxA + maxB) / 160.0))
                count += weight
                sumX += Double(x) * weight
                sumY += Double(y) * weight
                minX = min(minX, Double(x))
                minY = min(minY, Double(y))
                maxX = max(maxX, Double(x))
                maxY = max(maxY, Double(y))
            }
        }
    }

    if count < 10 {
        return nil
    }

    let centerX = sumX / count
    let centerY = sumY / count
    let boxW = max(160.0, min(Double(width) * 0.35, (maxX - minX) * 1.4))
    let boxH = max(160.0, min(Double(height) * 0.55, (maxY - minY) * 1.5))
    let x = max(0.0, min(Double(width) - boxW, centerX - boxW / 2))
    let y = max(0.0, min(Double(height) - boxH, centerY - boxH / 2))

    return FaceResult(
        x: x,
        y: y,
        width: boxW,
        height: boxH,
        confidence: Float(min(1.0, count / 5000.0)),
        kind: "skin",
        imageWidth: width,
        imageHeight: height
    )
}

func coreImageFaces(url: URL, image: CGImage) -> [FaceResult] {
    guard let ciImage = CIImage(contentsOf: url),
          let detector = CIDetector(
            ofType: CIDetectorTypeFace,
            context: nil,
            options: [CIDetectorAccuracy: CIDetectorAccuracyHigh]
          ) else {
        return []
    }
    return detector.features(in: ciImage).compactMap { feature in
        guard feature.type == CIFeatureTypeFace else {
            return nil
        }
        let bounds = feature.bounds
        let imageWidth = image.width
        let imageHeight = image.height
        return FaceResult(
            x: bounds.origin.x,
            y: Double(imageHeight) - bounds.origin.y - bounds.height,
            width: bounds.width,
            height: bounds.height,
            confidence: 0.8,
            kind: "coreimage_face",
            imageWidth: imageWidth,
            imageHeight: imageHeight
        )
    }
}

let request = VNDetectFaceRectanglesRequest()
request.usesCPUOnly = true
let handler = VNImageRequestHandler(cgImage: image, orientation: .up, options: [:])
do {
    try handler.perform([request])
} catch {
    FileHandle.standardOutput.write("[]\n".data(using: .utf8)!)
    exit(0)
}

var faces = (request.results ?? []).map { obs in
    convert(obs, image: image, kind: "face")
}

if faces.isEmpty {
    faces = coreImageFaces(url: imageURL, image: image)
}

if faces.isEmpty {
    let humanRequest = VNDetectHumanRectanglesRequest()
    humanRequest.usesCPUOnly = true
    do {
        try handler.perform([humanRequest])
        faces = (humanRequest.results ?? []).map { obs in
            convert(obs, image: image, kind: "human")
        }
    } catch {
        faces = []
    }
}

if faces.isEmpty {
    let saliencyRequest = VNGenerateAttentionBasedSaliencyImageRequest()
    saliencyRequest.usesCPUOnly = true
    do {
        try handler.perform([saliencyRequest])
        if let observation = saliencyRequest.results?.first {
            faces = (observation.salientObjects ?? []).map { obs in
                convert(obs, image: image, kind: "saliency")
            }
        }
    } catch {
        faces = []
    }
}

if faces.isEmpty, let skin = skinFallback(image: image) {
    faces = [skin]
}

do {
    let data = try JSONEncoder().encode(faces)
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
} catch {
    FileHandle.standardOutput.write("[]\n".data(using: .utf8)!)
}
