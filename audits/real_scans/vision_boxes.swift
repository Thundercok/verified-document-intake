// Apple Vision text observations with their boxes: image paths on stdin, one JSON object per line.
//
// Build: swiftc -O audits/real_scans/vision_boxes.swift -o audits/real_scans/work/vision_boxes
// Run:   audits/real_scans/work/vision_boxes [--jobs 4] < paths.txt > boxes.jsonl
//
// Same recognizer settings as audits/ocr_pilot/vision_ocr.swift (accurate, vi-VT, language
// correction on). Each record: path, and obs = [{text, x, y, w, h}] with the box in image
// fractions, origin top-left. v10 uses it to find the "Số: …" line and crop it for a third reader.

import Foundation
import Vision

struct Obs: Encodable {
    let text: String
    let x: Double
    let y: Double
    let w: Double
    let h: Double
}

struct Record: Encodable {
    let path: String
    let obs: [Obs]
    let error: String?
}

var jobs = 4
var args = CommandLine.arguments.dropFirst()
while let a = args.popFirst() {
    if a == "--jobs", let n = args.popFirst(), let v = Int(n) { jobs = v }
}

var paths: [String] = []
while let line = readLine() {
    let p = line.trimmingCharacters(in: .whitespaces)
    if !p.isEmpty { paths.append(p) }
}

func recognize(_ path: String) -> Record {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["vi-VT"]
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path), options: [:])
    do {
        try handler.perform([request])
    } catch {
        return Record(path: path, obs: [], error: "\(error)")
    }
    let obs: [Obs] = (request.results ?? []).compactMap { o in
        guard let t = o.topCandidates(1).first else { return nil }
        let b = o.boundingBox
        return Obs(text: t.string, x: b.minX, y: 1 - b.maxY, w: b.width, h: b.height)
    }
    return Record(path: path, obs: obs, error: nil)
}

var results = [Record?](repeating: nil, count: paths.count)
let lock = NSLock()
let chunk = max(1, (paths.count + jobs - 1) / jobs)
DispatchQueue.concurrentPerform(iterations: jobs) { j in
    let lo = j * chunk
    let hi = min(paths.count, lo + chunk)
    if lo >= hi { return }
    for i in lo..<hi {
        let r = autoreleasepool { recognize(paths[i]) }
        lock.lock()
        results[i] = r
        lock.unlock()
    }
}

let encoder = JSONEncoder()
for r in results {
    if let r = r, let data = try? encoder.encode(r) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write("\n".data(using: .utf8)!)
    }
}
