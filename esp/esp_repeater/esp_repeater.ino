#include "painlessMesh.h"

#define   MESH_PREFIX     "Monitor"
#define   MESH_PASSWORD   "12345678"
#define   MESH_PORT       5555

painlessMesh  mesh;

void receivedCallback( uint32_t from, String &msg ) {
  Serial.print(msg);
}
void newConnectionCallback(uint32_t nodeId) {
}
void changedConnectionCallback() {
}
void nodeTimeAdjustedCallback(int32_t offset) {
}

void setup() {
  Serial.setRxBufferSize(16384);
  Serial.begin(115200);
  Serial.setTimeout(100000);
  mesh.setDebugMsgTypes( ERROR );

  mesh.init( MESH_PREFIX, MESH_PASSWORD, MESH_PORT );
  mesh.onReceive(&receivedCallback);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);
  mesh.onNodeTimeAdjusted(&nodeTimeAdjustedCallback);
}

void loop() {
  mesh.update();
}
