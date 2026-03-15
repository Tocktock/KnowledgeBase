'use client'

import { create } from 'zustand'

type UiState = {
  commandOpen: boolean
  mobileSidebarOpen: boolean
  setCommandOpen: (open: boolean) => void
  setMobileSidebarOpen: (open: boolean) => void
}

export const useUiStore = create<UiState>((set) => ({
  commandOpen: false,
  mobileSidebarOpen: false,
  setCommandOpen: (open) => set({ commandOpen: open }),
  setMobileSidebarOpen: (open) => set({ mobileSidebarOpen: open }),
}))
