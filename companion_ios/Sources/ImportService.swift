//
//  ImportService.swift — ingestión al carrete con PhotoKit + ViewModel.
//
//  Pieza clave de la ruta B. Una app con permiso de "añadir" puede crear
//  assets vía PHAssetCreationRequest. Para Live Photos añade dos resources al
//  mismo asset: .photo (HEIC) + .pairedVideo (MOV) -> Live Photo nativa.
//
//  Nota sobre Live Photos: el emparejamiento requiere que el .HEIC y el .MOV
//  conserven su "content identifier" original (metadatos que iOS escribió al
//  capturarlas). PhotoBridge exporta ORIGINALES sin recomprimir, por lo que ese
//  identificador se preserva y el par se reconstruye correctamente.
//

import Foundation
import Photos
import Combine

struct PendingItem {
    let baseName: String
    var imageURL: URL?
    var videoURL: URL?
    var isLivePhoto: Bool { imageURL != nil && videoURL != nil }
}

enum InboxScanner {
    static let imageExts: Set<String> = ["heic", "heif", "jpg", "jpeg", "png"]
    static let videoExts: Set<String> = ["mov", "mp4", "m4v"]

    static var inboxURL: URL {
        let docs = FileManager.default.urls(for: .documentDirectory,
                                            in: .userDomainMask)[0]
        let inbox = docs.appendingPathComponent("inbox", isDirectory: true)
        try? FileManager.default.createDirectory(at: inbox,
                                                 withIntermediateDirectories: true)
        return inbox
    }

    /// Agrupa por nombre base para detectar Live Photos (imagen + .mov gemelo).
    static func scan() -> [PendingItem] {
        let fm = FileManager.default
        let inbox = inboxURL

        print("[InboxScanner] Buscando en: \(inbox.path)")
        print("[InboxScanner] inbox existe: \(fm.fileExists(atPath: inbox.path))")

        // Intentar con contentsOfDirectory(atPath:) — variante string, más básica
        let names: [String]
        do {
            names = try fm.contentsOfDirectory(atPath: inbox.path)
            print("[InboxScanner] contentsOfDirectory(atPath:) -> \(names.count) archivos")
            if !names.isEmpty { print("[InboxScanner] Primeros 3: \(Array(names.prefix(3)))") }
        } catch {
            print("[InboxScanner] ERROR contentsOfDirectory: \(error)")
            return []
        }

        var groups: [String: PendingItem] = [:]
        for name in names {
            let url = inbox.appendingPathComponent(name)
            let ext = (name as NSString).pathExtension.lowercased()
            let base = (name as NSString).deletingPathExtension
            var item = groups[base] ?? PendingItem(baseName: base,
                                                   imageURL: nil, videoURL: nil)
            if imageExts.contains(ext) { item.imageURL = url }
            else if videoExts.contains(ext) { item.videoURL = url }
            groups[base] = item
        }
        let result = Array(groups.values).filter { $0.imageURL != nil || $0.videoURL != nil }
        print("[InboxScanner] -> \(result.count) items en cola")
        return result
    }
}

@MainActor
final class ImportViewModel: ObservableObject {
    @Published var pendingCount = 0
    @Published var livePending = 0
    @Published var isImporting = false
    @Published var done = 0
    @Published var total = 0
    @Published var lastResult = ""

    private var items: [PendingItem] = []

    func refresh() {
        items = InboxScanner.scan()
        pendingCount = items.count
        livePending = items.filter { $0.isLivePhoto }.count
    }

    func startImport() {
        guard !items.isEmpty else { return }
        isImporting = true
        done = 0
        total = items.count
        lastResult = ""

        Task {
            let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
            guard status == .authorized || status == .limited else {
                self.finish(ok: 0, errors: ["Sin permiso de biblioteca de fotos"])
                return
            }

            var ok = 0
            var errors: [String] = []
            for item in items {
                do {
                    try await ingest(item)
                    ok += 1
                    // Mover los archivos ya ingeridos fuera del inbox
                    cleanup(item)
                } catch {
                    errors.append("\(item.baseName): \(error.localizedDescription)")
                }
                done += 1
            }
            self.finish(ok: ok, errors: errors)
        }
    }

    private func ingest(_ item: PendingItem) async throws {
        try await PHPhotoLibrary.shared().performChanges {
            let req = PHAssetCreationRequest.forAsset()
            let opts = PHAssetResourceCreationOptions()
            opts.shouldMoveFile = false   // preserva el archivo y su EXIF

            if item.isLivePhoto {
                req.addResource(with: .photo, fileURL: item.imageURL!, options: opts)
                req.addResource(with: .pairedVideo, fileURL: item.videoURL!, options: opts)
            } else if let img = item.imageURL {
                req.addResource(with: .photo, fileURL: img, options: opts)
            } else if let vid = item.videoURL {
                req.addResource(with: .video, fileURL: vid, options: opts)
            }
        }
    }

    private func cleanup(_ item: PendingItem) {
        for url in [item.imageURL, item.videoURL].compactMap({ $0 }) {
            try? FileManager.default.removeItem(at: url)
        }
    }

    private func finish(ok: Int, errors: [String]) {
        isImporting = false
        var msg = "Importadas \(ok)/\(total) al carrete."
        if !errors.isEmpty { msg += "\n\(errors.count) con error." }
        lastResult = msg
        refresh()
    }
}
