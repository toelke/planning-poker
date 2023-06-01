import { defineStore } from 'pinia';

export const useGameStore = defineStore('game', {
  state: () => ({
    participants: {},
    opened: false,
  }),
  getters: {
  },
  actions: {
    set_state(participants, opened) {
      this.opened = opened;
      this.participants = participants;
    },
  },
});
