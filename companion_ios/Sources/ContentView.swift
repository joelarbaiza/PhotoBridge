//
//  ContentView.swift — UI de la app companion.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var vm = ImportViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                header

                statusCard

                if vm.isImporting {
                    ProgressView(value: Double(vm.done),
                                 total: Double(max(vm.total, 1)))
                        .padding(.horizontal)
                    Text("Importando \(vm.done)/\(vm.total)…")
                        .font(.footnote).foregroundStyle(.secondary)
                }

                Button(action: { vm.startImport() }) {
                    Text(vm.isImporting ? "Importando…" : "Importar al carrete")
                        .frame(maxWidth: .infinity)
                        .padding()
                }
                .buttonStyle(.borderedProminent)
                .disabled(vm.isImporting || vm.pendingCount == 0)
                .padding(.horizontal)

                if !vm.lastResult.isEmpty {
                    Text(vm.lastResult)
                        .font(.callout)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal)
                }

                Spacer()
            }
            .padding(.top)
            .navigationTitle("PhotoBridge")
            .onAppear { vm.refresh() }
            .toolbar {
                Button("Refrescar") { vm.refresh() }
            }
        }
    }

    private var header: some View {
        VStack(spacing: 6) {
            Image(systemName: "photo.on.rectangle.angled")
                .font(.system(size: 44))
                .foregroundStyle(.tint)
            Text("Importa tus fotos al carrete conservando\nfecha, ubicación y Live Photos.")
                .font(.footnote)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
    }

    private var statusCard: some View {
        VStack(spacing: 8) {
            Text("\(vm.pendingCount)")
                .font(.system(size: 40, weight: .bold))
            Text("elementos en cola")
                .font(.subheadline).foregroundStyle(.secondary)
            if vm.livePending > 0 {
                Text("incluye \(vm.livePending) Live Photos")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 20)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
        .padding(.horizontal)
    }
}
