<template>
  <q-page
    v-bind:class="
      store.participants[myId] &&
      store.participants[myId].points === false &&
      Object.keys(store.participants)
        .filter((key) => key != myId)
        .every((key) => store.participants[key].points) &&
      Object.keys(store.participants).filter(
        (key) => !store.participants[key].spectator
      ).length > 1
        ? 'bg-red-3 col q-pa-sm'
        : 'col q-pa-sm'
    "
  >
    <div class="row">
      <div class="col">
        <q-btn
          v-for="btn in [1, 2, 3, 5, 8, 13, 21]"
          v-bind:key="btn"
          @click="select(btn)"
          :color="btn == myPoints ? 'deep-orange' : 'primary'"
          :disabled="store.opened || spectator"
          >{{ btn }}</q-btn
        >
      </div>
      <div class="col">
        <q-btn class="bg-white" @click="clear()">Clear</q-btn>
        <q-btn class="bg-white" @click="open()">Open</q-btn>
      </div>
      <div class="col">
        <q-checkbox v-model="spectator" label="I am just a spectator" />
        <q-input
          class="q-pl-sm"
          debounce="1000"
          label="Your name:"
          v-model="userName"
          :disable="spectator"
        />
      </div>
    </div>
    <div class="row q-pa-sm">
      <div v-for="id in Object.keys(store.participants)" v-bind:key="id" class="q-pa-sm">
        <q-card>
          <q-card-section class="bg-primary text-white">
            {{ store.participants[id].userName
            }}<span v-if="id == myId"> (You!)</span>
          </q-card-section>
          <q-card-section>
            <span v-if="store.participants[id].points === true">
              Card Selected</span
            >
            <span v-if="store.opened">
              {{ store.participants[id].points }}</span
            ></q-card-section
          >
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script lang="ts">
import { defineComponent, ref, watchEffect } from 'vue';
import { useGameStore } from 'stores/game-store';
import axios from 'axios';
import { useQuasar } from 'quasar';
import { v4 as uuidv4 } from 'uuid';

const store = useGameStore();

const myId = ref(uuidv4());

var userName = ref('');
var spectator = ref(false);
var myPoints = ref(undefined);

watchEffect(function () {
  if (!userName.value) {
    return;
  }

  axios.post(`/api/participant/${myId.value}/userName`, {
    userName: userName.value,
  });
  window.localStorage.setItem('userName', userName.value);
});

watchEffect(function () {
  if (!store.participants[myId.value]?.points) {
    myPoints.value = null;
  }
});
var update_spectator = function () {
  axios.post(`/api/participant/${myId.value}/spectator`, {
    spectator: spectator.value,
  });
  window.localStorage.setItem('spectator', spectator.value);
};

export default defineComponent({
  name: 'IndexPage',
  components: {},
  setup() {
    const open = function () {
      axios.post('/api/open');
    };
    const clear = function () {
      axios.post('/api/clear');
    };
    const select = function (points) {
      if (myPoints.value == points) {
        myPoints.value = null;
      } else {
        myPoints.value = points;
      }
      this.connection.send(JSON.stringify({ points: myPoints.value }));
    };
    return { store, userName, myId, select, myPoints, open, clear, spectator };
  },
  created: function () {
    var loc = window.location,
      new_uri;
    if (loc.protocol === 'https:') {
      new_uri = 'wss:';
    } else {
      new_uri = 'ws:';
    }
    new_uri += '//' + loc.host;
    new_uri += `/api/participant/${myId.value}`;
    this.connection = new WebSocket(new_uri);

    this.connection.onmessage = function (event) {
      event = JSON.parse(event.data);
      if (!event.hasOwnProperty('error')) {
        store.set_state(event.participants, event.opened);
      }
    };

    const $q = useQuasar();
    this.connection.onopen = function () {
      if ($q.localStorage.has('userName')) {
        userName.value = $q.localStorage.getItem('userName');
      }
      if ($q.localStorage.has('spectator')) {
        spectator.value = $q.localStorage.getItem('spectator') == 'true';
      }
      watchEffect(update_spectator);
    };
  },
});
</script>
