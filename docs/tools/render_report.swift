import AppKit
import CoreGraphics
import CoreText
import Foundation

let arguments = CommandLine.arguments
guard arguments.count == 3 else {
    fputs("usage: swift render_report.swift input.md output.pdf\n", stderr)
    exit(2)
}

let inputURL = URL(fileURLWithPath: arguments[1])
let outputURL = URL(fileURLWithPath: arguments[2])
let markdown = try String(contentsOf: inputURL, encoding: .utf8)

let pageWidth: CGFloat = 595.28
let pageHeight: CGFloat = 841.89
let marginX: CGFloat = 54
let marginTop: CGFloat = 66
let marginBottom: CGFloat = 54
let bodyRect = CGRect(
    x: marginX,
    y: marginBottom,
    width: pageWidth - marginX * 2,
    height: pageHeight - marginTop - marginBottom
)

let navy = NSColor(calibratedRed: 0.055, green: 0.105, blue: 0.185, alpha: 1)
let blue = NSColor(calibratedRed: 0.075, green: 0.365, blue: 0.745, alpha: 1)
let teal = NSColor(calibratedRed: 0.02, green: 0.55, blue: 0.49, alpha: 1)
let ink = NSColor(calibratedWhite: 0.12, alpha: 1)
let muted = NSColor(calibratedWhite: 0.38, alpha: 1)
let rule = NSColor(calibratedWhite: 0.84, alpha: 1)

func font(_ size: CGFloat, weight: NSFont.Weight = .regular, mono: Bool = false) -> NSFont {
    if mono {
        return NSFont.monospacedSystemFont(ofSize: size, weight: weight)
    }
    if let korean = NSFont(name: "Apple SD Gothic Neo", size: size) {
        if weight == .bold || weight == .semibold {
            return NSFontManager.shared.convert(korean, toHaveTrait: .boldFontMask)
        }
        return korean
    }
    return NSFont.systemFont(ofSize: size, weight: weight)
}

func attributes(
    size: CGFloat,
    weight: NSFont.Weight = .regular,
    color: NSColor = ink,
    spacing: CGFloat = 4,
    before: CGFloat = 0,
    after: CGFloat = 0,
    indent: CGFloat = 0,
    mono: Bool = false
) -> [NSAttributedString.Key: Any] {
    let paragraph = NSMutableParagraphStyle()
    paragraph.lineSpacing = spacing
    paragraph.paragraphSpacingBefore = before
    paragraph.paragraphSpacing = after
    paragraph.firstLineHeadIndent = indent
    paragraph.headIndent = indent
    paragraph.tailIndent = 0
    paragraph.lineBreakMode = .byWordWrapping
    return [
        .font: font(size, weight: weight, mono: mono),
        .foregroundColor: color,
        .paragraphStyle: paragraph
    ]
}

func clean(_ text: String) -> String {
    text.replacingOccurrences(of: "**", with: "")
        .replacingOccurrences(of: "`", with: "")
}

let body = NSMutableAttributedString()
var inCode = false
var reachedContent = false

for rawLine in markdown.components(separatedBy: .newlines) {
    let line = rawLine.trimmingCharacters(in: .whitespaces)

    if line.hasPrefix("## 1.") { reachedContent = true }
    if !reachedContent { continue }

    if line.hasPrefix("```") {
        inCode.toggle()
        if !inCode { body.append(NSAttributedString(string: "\n")) }
        continue
    }

    if inCode {
        body.append(NSAttributedString(
            string: rawLine + "\n",
            attributes: attributes(size: 8.2, color: navy, spacing: 2, mono: true)
        ))
        continue
    }

    if line.isEmpty {
        body.append(NSAttributedString(string: "\n", attributes: attributes(size: 4, spacing: 0)))
    } else if line == "---" {
        body.append(NSAttributedString(string: "\n", attributes: attributes(size: 2, spacing: 0, after: 4)))
    } else if line.hasPrefix("## ") {
        body.append(NSAttributedString(
            string: clean(String(line.dropFirst(3))) + "\n",
            attributes: attributes(size: 19, weight: .bold, color: navy, spacing: 2, before: 14, after: 7)
        ))
    } else if line.hasPrefix("### ") {
        body.append(NSAttributedString(
            string: clean(String(line.dropFirst(4))) + "\n",
            attributes: attributes(size: 13.5, weight: .semibold, color: blue, spacing: 2, before: 9, after: 4)
        ))
    } else if line.hasPrefix("- ") {
        body.append(NSAttributedString(
            string: "• " + clean(String(line.dropFirst(2))) + "\n",
            attributes: attributes(size: 9.7, spacing: 3, after: 1, indent: 13)
        ))
    } else if line.range(of: #"^\d+\. "#, options: .regularExpression) != nil {
        body.append(NSAttributedString(
            string: clean(line) + "\n",
            attributes: attributes(size: 9.7, weight: .semibold, spacing: 3, after: 2, indent: 12)
        ))
    } else if line.hasPrefix("|") {
        body.append(NSAttributedString(
            string: clean(line) + "\n",
            attributes: attributes(size: 7.25, color: navy, spacing: 1.5, mono: true)
        ))
    } else {
        body.append(NSAttributedString(
            string: clean(line) + "\n",
            attributes: attributes(size: 9.7, spacing: 3.4, after: 3)
        ))
    }
}

var mediaBox = CGRect(x: 0, y: 0, width: pageWidth, height: pageHeight)
guard let consumer = CGDataConsumer(url: outputURL as CFURL),
      let context = CGContext(consumer: consumer, mediaBox: &mediaBox, nil) else {
    fputs("failed to create PDF context\n", stderr)
    exit(3)
}

func drawText(_ context: CGContext, _ text: String, x: CGFloat, y: CGFloat, size: CGFloat, weight: NSFont.Weight, color: NSColor) {
    let attributed = NSAttributedString(string: text, attributes: [
        .font: font(size, weight: weight),
        .foregroundColor: color
    ])
    let line = CTLineCreateWithAttributedString(attributed)
    context.textPosition = CGPoint(x: x, y: y)
    CTLineDraw(line, context)
}

func beginPage(_ context: CGContext) {
    context.beginPDFPage(nil)
    context.setFillColor(NSColor.white.cgColor)
    context.fill(mediaBox)
}

// Cover
beginPage(context)
context.setFillColor(navy.cgColor)
context.fill(CGRect(x: 0, y: 0, width: pageWidth, height: pageHeight))
context.setFillColor(blue.cgColor)
context.fill(CGRect(x: 0, y: pageHeight - 18, width: pageWidth, height: 18))
context.setFillColor(teal.cgColor)
context.fill(CGRect(x: 54, y: 270, width: 104, height: 5))
drawText(context, "STOCK REPORTS LAB", x: 54, y: 715, size: 12, weight: .semibold, color: teal)
drawText(context, "기획·아키텍처", x: 54, y: 625, size: 36, weight: .bold, color: .white)
drawText(context, "보고서", x: 54, y: 580, size: 36, weight: .bold, color: .white)
drawText(context, "KRX 장 마감 골든크로스 리포트 MVP", x: 54, y: 525, size: 16, weight: .regular, color: NSColor(calibratedWhite: 0.82, alpha: 1))
drawText(context, "Version 2.0", x: 54, y: 238, size: 13, weight: .semibold, color: .white)
drawText(context, "2026-06-21", x: 54, y: 214, size: 11, weight: .regular, color: NSColor(calibratedWhite: 0.72, alpha: 1))
drawText(context, "MVP 의사결정 완료", x: 54, y: 176, size: 10, weight: .regular, color: teal)
context.endPDFPage()

// Body
let framesetter = CTFramesetterCreateWithAttributedString(body)
var location = 0
var pageNumber = 2
let totalLength = body.length

while location < totalLength {
    beginPage(context)

    drawText(context, "STOCK REPORTS LAB  /  PLAN v2.0", x: marginX, y: pageHeight - 35, size: 7.5, weight: .semibold, color: muted)
    context.setStrokeColor(rule.cgColor)
    context.setLineWidth(0.6)
    context.move(to: CGPoint(x: marginX, y: pageHeight - 45))
    context.addLine(to: CGPoint(x: pageWidth - marginX, y: pageHeight - 45))
    context.strokePath()

    let path = CGPath(rect: bodyRect, transform: nil)
    let frame = CTFramesetterCreateFrame(framesetter, CFRange(location: location, length: 0), path, nil)
    CTFrameDraw(frame, context)
    let visible = CTFrameGetVisibleStringRange(frame)
    if visible.length == 0 { break }
    location += visible.length

    context.setStrokeColor(rule.cgColor)
    context.move(to: CGPoint(x: marginX, y: 35))
    context.addLine(to: CGPoint(x: pageWidth - marginX, y: 35))
    context.strokePath()
    drawText(context, "확정 기획 보고서", x: marginX, y: 18, size: 7.5, weight: .regular, color: muted)
    drawText(context, String(pageNumber), x: pageWidth - marginX - 10, y: 18, size: 7.5, weight: .semibold, color: muted)

    context.endPDFPage()
    pageNumber += 1
}

context.closePDF()
print("created \(outputURL.path), pages: \(pageNumber - 1)")
