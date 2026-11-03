import AppKit
import PDFKit
import Foundation

let input = "/Users/tarushchauhan/Library/Containers/net.whatsapp.WhatsApp/Data/tmp/documents/1DE2BBDE-CB91-45F5-BB1F-6F18FF01EFF5/CI (1).pdf"
let output = "/Users/tarushchauhan/Documents/New project/latex_paper/figures/methodology.png"

guard
    let doc = PDFDocument(url: URL(fileURLWithPath: input)),
    let page = doc.page(at: 2)
else {
    fputs("Failed to open PDF/page\n", stderr)
    exit(1)
}

let cropBox = CGRect(x: 120, y: 500, width: 380, height: 250)
let scale: CGFloat = 3.0
let width = Int(cropBox.width * scale)
let height = Int(cropBox.height * scale)

guard let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: width,
    pixelsHigh: height,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
) else {
    fputs("Failed to create bitmap\n", stderr)
    exit(1)
}

rep.size = NSSize(width: cropBox.width, height: cropBox.height)

NSGraphicsContext.saveGraphicsState()
guard let context = NSGraphicsContext(bitmapImageRep: rep) else {
    fputs("Failed to create graphics context\n", stderr)
    exit(1)
}
NSGraphicsContext.current = context

let cg = context.cgContext
cg.setFillColor(NSColor.white.cgColor)
cg.fill(CGRect(x: 0, y: 0, width: cropBox.width * scale, height: cropBox.height * scale))
cg.scaleBy(x: scale, y: scale)
cg.translateBy(x: -cropBox.minX, y: -cropBox.minY)
page.draw(with: .mediaBox, to: cg)

NSGraphicsContext.restoreGraphicsState()

guard let data = rep.representation(using: .png, properties: [:]) else {
    fputs("Failed to encode PNG\n", stderr)
    exit(1)
}

try data.write(to: URL(fileURLWithPath: output))
print(output)
