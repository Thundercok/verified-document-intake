// Batch Apple Vision OCR for the pilot: image paths on stdin, one JSON object per line on stdout.
//
// Build: swiftc -O audits/ocr_pilot/vision_ocr.swift -o audits/ocr_pilot/work/vision_ocr
// Run:   audits/ocr_pilot/work/vision_ocr [--no-correction] [--jobs 4] < paths.txt > vision.jsonl
//
// Each record: path, text (observations in reading order joined by a space), conf_min and
// conf_mean over observations, and up to three alternative strings when the crop is one line.

import Foundation
import Vision

struct Record: Encodable {
    let path: String
    let text: String
    let conf_min: Float
    let conf_mean: Float
    let n_obs: Int
    let alts: [String]
    let error: String?
}

var correction = true
var jobs = 4
var args = CommandLine.arguments.dropFirst()
while let a = args.popFirst() {
    if a == "--no-correction" { correction = false }
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
    request.usesLanguageCorrection = correction
    request.recognitionLanguages = ["vi-VT"]
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path), options: [:])
    do {
        try handler.perform([request])
    } catch {
        return Record(path: path, text: "", conf_min: 0, conf_mean: 0, n_obs: 0, alts: [], error: "\(error)")
    }
    // Reading order: top to bottom (Vision's origin is bottom-left), then left to right.
    let obs = (request.results ?? []).sorted {
        abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.02
            ? $0.boundingBox.midY > $1.boundingBox.midY : $0.boundingBox.minX < $1.boundingBox.minX
    }
    let tops = obs.compactMap { $0.topCandidates(1).first }
    let confs = tops.map { $0.confidence }
    let alts = obs.count == 1 ? obs[0].topCandidates(3).map { $0.string } : []
    return Record(
        path: path,
        text: tops.map { $0.string }.joined(separator: " "),
        conf_min: confs.min() ?? 0,
        conf_mean: confs.isEmpty ? 0 : confs.reduce(0, +) / Float(confs.count),
        n_obs: obs.count,
        alts: alts,
        error: nil
    )
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
