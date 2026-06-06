//
//  PhotoBridgeApp.swift — punto de entrada de la app companion (ruta B).
//
//  Esta app vive en el iPhone. El PC le empuja los archivos exportados a su
//  sandbox (Documents/inbox) vía house_arrest; aquí se ingestan al carrete con
//  PhotoKit, reconstruyendo Live Photos nativas y conservando metadatos.
//

import SwiftUI

@main
struct PhotoBridgeApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
