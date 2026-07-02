import AppKit

struct SubtitleSpec {
    let label: String
    let korean: String
    let romanization: String
    let english: String
}

func drawCenteredText(
    _ text: String,
    font: NSFont,
    fill: NSColor,
    stroke: NSColor? = nil,
    strokeWidth: CGFloat = 0,
    y: CGFloat,
    canvasWidth: CGFloat
) {
    var attributes: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: fill
    ]
    if let stroke {
        attributes[.strokeColor] = stroke
        attributes[.strokeWidth] = -strokeWidth
    }
    let attributed = NSAttributedString(string: text, attributes: attributes)
    let size = attributed.size()
    attributed.draw(at: CGPoint(x: (canvasWidth - size.width) / 2, y: y))
}

func drawCenteredText(
    _ text: String,
    font: NSFont,
    fill: NSColor,
    stroke: NSColor,
    strokeWidth: CGFloat,
    y: CGFloat,
    canvasWidth: CGFloat,
    scaleY: CGFloat
) {
    let attributes: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: fill,
        .strokeColor: stroke,
        .strokeWidth: -strokeWidth
    ]
    let attributed = NSAttributedString(string: text, attributes: attributes)
    let size = attributed.size()
    NSGraphicsContext.current?.saveGraphicsState()
    let transform = NSAffineTransform()
    transform.translateX(by: (canvasWidth - size.width) / 2, yBy: y)
    transform.scaleX(by: 1, yBy: scaleY)
    transform.concat()
    attributed.draw(at: .zero)
    NSGraphicsContext.current?.restoreGraphicsState()
}

func textSize(_ text: String, font: NSFont) -> CGSize {
    return NSAttributedString(string: text, attributes: [.font: font]).size()
}

let args = CommandLine.arguments
guard args.count >= 4 else {
    fputs("usage: RenderSubtitleOverlay <output.png> <korean> <romanization> [english] [label]\n", stderr)
    exit(1)
}

let outputPath = args[1]
let spec = SubtitleSpec(
    label: args.count >= 6 ? args[5] : "Casual",
    korean: args[2],
    romanization: args[3],
    english: args.count >= 5 ? args[4] : ""
)

let width = 1080
let height = 1920
let image = NSImage(size: NSSize(width: width, height: height))
image.lockFocus()

NSColor.clear.setFill()
NSRect(x: 0, y: 0, width: width, height: height).fill()

let canvasWidth = CGFloat(width)

let labelFont = NSFont(name: "HelveticaNeue-Bold", size: 67) ?? NSFont(name: "Arial-BoldMT", size: 67) ?? NSFont.boldSystemFont(ofSize: 67)
let koreanFont = NSFont(name: "AppleSDGothicNeo-Heavy", size: 102) ?? NSFont(name: "AppleSDGothicNeo-Bold", size: 102) ?? NSFont.boldSystemFont(ofSize: 102)
let romanFont = NSFont(name: "Arial-BoldMT", size: 54) ?? NSFont.boldSystemFont(ofSize: 54)
let englishFont = NSFont(name: "Arial-BoldMT", size: 77) ?? NSFont.boldSystemFont(ofSize: 77)

// AppKit's drawing origin is bottom-left. These values are scaled from the
// reference video's 576x1024 vocabulary stack to this 1080x1920 output.
let labelY: CGFloat = 874
let boxY: CGFloat = 709
let romanY: CGFloat = 631
let englishY: CGFloat = 517

let koreanSize = textSize(spec.korean, font: koreanFont)
let boxWidth: CGFloat = max(koreanSize.width + 72, 405)
let boxHeight: CGFloat = 148
let boxRect = NSRect(
    x: (canvasWidth - boxWidth) / 2,
    y: boxY,
    width: boxWidth,
    height: boxHeight
)

let shadow = NSShadow()
shadow.shadowColor = NSColor.black.withAlphaComponent(0.42)
shadow.shadowBlurRadius = 5
shadow.shadowOffset = NSSize(width: 0, height: -2)

NSGraphicsContext.current?.saveGraphicsState()
shadow.set()
let roundedBox = NSBezierPath(roundedRect: boxRect, xRadius: 10, yRadius: 10)
NSColor.white.setFill()
roundedBox.fill()
NSGraphicsContext.current?.restoreGraphicsState()

drawCenteredText(
    spec.label,
    font: labelFont,
    fill: NSColor(calibratedRed: 255.0 / 255.0, green: 183.0 / 255.0, blue: 209.0 / 255.0, alpha: 1.0),
    stroke: .black,
    strokeWidth: 4.2,
    y: labelY,
    canvasWidth: canvasWidth,
    scaleY: 1.23
)

drawCenteredText(
    spec.korean,
    font: koreanFont,
    fill: NSColor(calibratedRed: 129.0 / 255.0, green: 0.0 / 255.0, blue: 255.0 / 255.0, alpha: 1.0),
    y: boxY + (boxHeight - koreanSize.height) / 2 - 6,
    canvasWidth: canvasWidth
)

drawCenteredText(
    spec.romanization,
    font: romanFont,
    fill: .white,
    stroke: .black,
    strokeWidth: 4.2,
    y: romanY,
    canvasWidth: canvasWidth
)

if !spec.english.isEmpty {
    drawCenteredText(
        spec.english,
        font: englishFont,
        fill: .white,
        stroke: .black,
        strokeWidth: 5.0,
        y: englishY,
        canvasWidth: canvasWidth
    )
}

image.unlockFocus()

guard
    let tiff = image.tiffRepresentation,
    let bitmap = NSBitmapImageRep(data: tiff),
    let png = bitmap.representation(using: .png, properties: [:])
else {
    fputs("failed to render png\n", stderr)
    exit(2)
}

try png.write(to: URL(fileURLWithPath: outputPath))
