// Render PDF pages to PNG with PDFKit, for the real-scan audit.
//
// Build: swiftc -O audits/real_scans/render_pages.swift -o audits/real_scans/work/render_pages
// Run:   render_pages [--dpi 300] < jobs.tsv
//        Each line: PDF path, TAB, page (1-based; 0 = last page), TAB, output PNG path.
//        Prints one line per job: output path, TAB, page count (or "ERR").

import AppKit
import Foundation
import PDFKit

var dpi: CGFloat = 300
var args = Array(CommandLine.arguments.dropFirst())
while !args.isEmpty {
    let a = args.removeFirst()
    if a == "--dpi", !args.isEmpty, let v = Double(args.removeFirst()) { dpi = CGFloat(v) }
}

while let line = readLine() {
    let p = line.split(separator: "\t").map(String.init)
    guard p.count == 3, let n = Int(p[1]) else { continue }
    guard let doc = PDFDocument(url: URL(fileURLWithPath: p[0])), doc.pageCount > 0 else {
        print("\(p[2])\tERR"); continue
    }
    let page = doc.page(at: n == 0 ? doc.pageCount - 1 : min(n, doc.pageCount) - 1)!
    let box = page.bounds(for: .mediaBox)
    let s = dpi / 72
    let w = Int(box.width * s), h = Int(box.height * s)
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpaceCreateDeviceRGB(),
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: s, y: s)
    page.draw(with: .mediaBox, to: ctx)
    let rep = NSBitmapImageRep(cgImage: ctx.makeImage()!)
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: p[2]))
    print("\(p[2])\t\(doc.pageCount)")
}
