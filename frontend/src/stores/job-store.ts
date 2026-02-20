import { create } from "zustand";

type JobStore = {
  activeJobId: string | null;
  setActiveJobId: (jobId: string | null) => void;
};

export const useJobStore = create<JobStore>((set) => ({
  activeJobId: null,
  setActiveJobId: (activeJobId) => set({ activeJobId })
}));
