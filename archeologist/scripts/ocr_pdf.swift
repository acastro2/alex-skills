// Print the text of an image-only PDF with macOS Vision OCR, one page after another.
// Usage: swift ocr_pdf.swift <file.pdf>
import Foundation
import PDFKit
import Vision

guard CommandLine.arguments.count == 2,
      let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    FileHandle.standardError.write("usage: swift ocr_pdf.swift <file.pdf>\n".data(using: .utf8)!)
    exit(1)
}

for i in 0..<doc.pageCount {
    guard let page = doc.page(at: i) else { continue }
    let box = page.bounds(for: .mediaBox)
    let scale = 2000 / max(box.width, box.height)
    let image = page.thumbnail(of: CGSize(width: box.width * scale, height: box.height * scale), for: .mediaBox)
    guard let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg).perform([request])
    let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    print("Page \(i + 1):")
    print(lines.joined(separator: "\n"))
}
