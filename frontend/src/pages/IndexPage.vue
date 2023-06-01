<template>
  <q-page class="col q-pa-sm">
    <div class="row">
      <div class="col">
        <q-btn
          v-for="btn in [1, 2, 3, 5, 8, 13, 21]"
          v-bind:key="btn"
          @click="select(btn)"
          :color="btn == myPoints ? 'deep-orange' : 'primary'"
          :disabled="store.opened"
          >{{ btn }}</q-btn
        >
      </div>
      <div class="col">
        <q-btn @click="clear()">Clear</q-btn>
        <q-btn @click="open()">Open</q-btn>
      </div>
      <div class="col">
        <q-input debounce="1000" label="Your name:" v-model="userName" />
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
    return { store, userName, myId, select, myPoints, open, clear };
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
    };
  },
});
</script>
