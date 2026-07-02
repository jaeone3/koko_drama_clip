import AppKit
import Foundation

struct Config {
    let personPath: String
    let outputPath: String
    let canvasWidth: Int
    let canvasHeight: Int
    let topX: CGFloat
    let topY: CGFloat
    let cardWidth: CGFloat
    let cardHeight: CGFloat
}

func parseConfig() -> Config {
    let args = CommandLine.arguments
    guard args.count == 9 else {
        fputs("""
        usage: render_image_card_overlay <person.png> <output.png> <canvas_w> <canvas_h> <top_x> <top_y> <card_w> <card_h>
        Coordinates are top-left based, in output video pixels.
        """, stderr)
        exit(1)
    }

    guard
        let canvasWidth = Int(args[3]),
        let canvasHeight = Int(args[4]),
        let topX = Double(args[5]),
        let topY = Double(args[6]),
        let cardWidth = Double(args[7]),
        let cardHeight = Double(args[8])
    else {
        fputs("invalid numeric argument\n", stderr)
        exit(1)
    }

    return Config(
        personPath: args[1],
        outputPath: args[2],
        canvasWidth: canvasWidth,
        canvasHeight: canvasHeight,
        topX: CGFloat(topX),
        topY: CGFloat(topY),
        cardWidth: CGFloat(cardWidth),
        cardHeight: CGFloat(cardHeight)
    )
}

let config = parseConfig()

guard let person = NSImage(contentsOfFile: config.personPath) else {
    fputs("failed to read person image\n", stderr)
    exit(2)
}

let canvasSize = NSSize(width: config.canvasWidth, height: config.canvasHeight)
let image = NSImage(size: canvasSize)
image.lockFocus()

NSColor.clear.setFill()
NSRect(origin: .zero, size: canvasSize).fill()

let cardBottomY = CGFloat(config.canvasHeight) - config.topY - config.cardHeight
let cardRect = NSRect(x: config.topX, y: cardBottomY, width: config.cardWidth, height: config.cardHeight)
let imageSlot = NSRect(x: cardRect.minX, y: cardRect.minY, width: cardRect.width * 0.30, height: cardRect.height)
let textSlot = NSRect(x: imageSlot.maxX, y: cardRect.minY, width: cardRect.width * 0.70, height: cardRect.height)

let personSize = min(imageSlot.width * 1.05, imageSlot.height * 0.94)
let personRect = NSRect(
    x: imageSlot.midX - personSize / 2,
    y: imageSlot.midY - personSize / 2,
    width: personSize,
    height: personSize
)
person.draw(in: personRect, from: .zero, operation: .sourceOver, fraction: 1.0)

let paragraph = NSMutableParagraphStyle()
paragraph.alignment = .left

let fontSize = min(textSlot.height * 0.34, textSlot.width * 0.15)
let textRect = NSRect(
    x: textSlot.minX + textSlot.width * 0.06,
    y: textSlot.midY - fontSize * 0.72,
    width: textSlot.width * 0.88,
    height: fontSize * 1.45
)

let textAttributes: [NSAttributedString.Key: Any] = [
    .font: NSFont(name: "HelveticaNeue-CondensedBlack", size: fontSize) ?? NSFont.boldSystemFont(ofSize: fontSize),
    .foregroundColor: NSColor(calibratedWhite: 0.06, alpha: 1),
    .strokeColor: NSColor.white.withAlphaComponent(0.80),
    .strokeWidth: -2.5,
    .paragraphStyle: paragraph,
]

"koko AI".draw(in: textRect, withAttributes: textAttributes)

image.unlockFocus()

guard
    let tiff = image.tiffRepresentation,
    let bitmap = NSBitmapImageRep(data: tiff),
    let png = bitmap.representation(using: .png, properties: [:])
else {
    fputs("failed to render output image\n", stderr)
    exit(3)
}

try png.write(to: URL(fileURLWithPath: config.outputPath))
