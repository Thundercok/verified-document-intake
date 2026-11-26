// QR codes for the CCCD QR test: draw them with CoreImage, read them with Apple Vision.
//
// Build: swiftc -O audits/cccd_qr/qr_tool.swift -o audits/cccd_qr/work/qr_tool
// Draw:  qr_tool gen [--level M] < jobs.tsv     (each line: output PNG path, TAB, payload in base64)
//        Writes a black-on-white code, 8 px per module, with a 4-module quiet zone.
// Read:  qr_tool read [--jobs 6] < paths.txt > reads.jsonl
//        Each record: path, payloads (Vision's decoded strings, one per QR code found), error.

import CoreImage
import Foundation
import ImageIO
import UniformTypeIdentifiers
import Vision

struct Read: Encodable {
    let path: String
    let payloads: [String]
    let error: String?
}

var args = Array(CommandLine.arguments.dropFirst())
guard let mode = args.first else {
    FileHandle.standardError.write("usage: qr_tool gen|read\n".data(using: .utf8)!)
    exit(2)
}
args.removeFirst()
var level = "M"
var jobs = 6
while !args.isEmpty {
    let a = args.removeFirst()
    if a == "--level", !args.isEmpty { level = args.removeFirst() }
    if a == "--jobs", !args.isEmpty, let v = Int(args.removeFirst()) { jobs = v }
}

var lines: [String] = []
while let l = readLine() { if !l.isEmpty { lines.append(l) } }

if mode == "gen" {
    let ctx = CIContext()
    for line in lines {
        let parts = line.split(separator: "\t", maxSplits: 1).map(String.init)
        guard parts.count == 2, let data = Data(base64Encoded: parts[1]),
              let f = CIFilter(name: "CIQRCodeGenerator")
        else { fatalError("bad job line") }
        f.setValue(data, forKey: "inputMessage")
        f.setValue(level, forKey: "inputCorrectionLevel")
        // CoreImage adds no quiet zone of its own beyond one module; pad to four.
        let code = f.outputImage!.transformed(by: CGAffineTransform(scaleX: 8, y: 8))
        let pad = CGFloat(8 * 4)
        let canvas = CIImage(color: .white)
            .cropped(to: code.extent.insetBy(dx: -pad, dy: -pad))
        let img = code.composited(over: canvas)
        let cg = ctx.createCGImage(img, from: img.extent, format: .L8,
                                   colorSpace: CGColorSpaceCreateDeviceGray())!
        let url = URL(fileURLWithPath: parts[0]) as CFURL
        let dest = CGImageDestinationCreateWithURL(url, UTType.png.identifier as CFString, 1, nil)!
        CGImageDestinationAddImage(dest, cg, nil)
        CGImageDestinationFinalize(dest)
    }
} else {
    var out = [Read?](repeating: nil, count: lines.count)
    let lock = NSLock()
    DispatchQueue.concurrentPerform(iterations: jobs) { w in
        for i in stride(from: w, to: lines.count, by: jobs) {
            let path = lines[i]
            let req = VNDetectBarcodesRequest()
            req.symbologies = [.qr]
            var rec: Read
            do {
                try VNImageRequestHandler(url: URL(fileURLWithPath: path)).perform([req])
                let ps = (req.results ?? []).compactMap { $0.payloadStringValue }
                rec = Read(path: path, payloads: ps, error: nil)
            } catch {
                rec = Read(path: path, payloads: [], error: "\(error)")
            }
            lock.lock(); out[i] = rec; lock.unlock()
        }
    }
    let enc = JSONEncoder()
    for r in out {
        print(String(data: try! enc.encode(r!), encoding: .utf8)!)
    }
}
