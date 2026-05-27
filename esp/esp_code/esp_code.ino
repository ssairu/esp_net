#include "painlessMesh.h"

#define   MESH_PREFIX     "Monitor"
#define   MESH_PASSWORD   "12345678"
#define   MESH_PORT       5555
#define LED_BUILTIN 2

Scheduler userScheduler;
painlessMesh  mesh;

void checkStart();
void checkEnd();
void parseMessage();
void sendMessage();

Task taskSendMessage( TASK_IMMEDIATE , TASK_FOREVER, &checkStart);

String msg = "";
char s1 = 0;
char s2 = 0;
char s3 = 0;

void updateTOP(char c){
  s1 = s2;
  s2 = s3;
  s3 = c;
}

void clearBUF(){
  s1 = 0;
  s2 = 0;
  s3 = 0;
}

void checkStart(){
  if (Serial.available()){
    char s = char(Serial.read());
    updateTOP(s);

    if (s1 == '&' && s2 == '$' && s3 == '&'){
      msg = "&$&";
      clearBUF();
      digitalWrite(LED_BUILTIN, HIGH); 
      taskSendMessage.setCallback(&parseMessage);
    }
  }
}

void parseMessage(){
  char character;
  char i = 0;
  while (Serial.available() && i < 50){
    character = char(Serial.read());
    updateTOP(character);

    msg = msg + character;
    i++;
    if (s1 == '%' && s2 == '@' && s3 == '%'){
      taskSendMessage.setCallback(&sendMessage);
      break;
    }
  }  
}

void sendMessage(){
  digitalWrite(LED_BUILTIN, LOW);
  mesh.sendBroadcast( msg );  
  msg = "";
  taskSendMessage.setCallback(&checkStart);
}




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
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  // mesh.setDebugMsgTypes( ERROR | MESH_STATUS | CONNECTION | SYNC | COMMUNICATION | GENERAL | MSG_TYPES | REMOTE ); // all types on
 mesh.setDebugMsgTypes( ERROR );  // set before init() so that you can see startup messages

  mesh.init( MESH_PREFIX, MESH_PASSWORD, &userScheduler, MESH_PORT );
  mesh.onReceive(&receivedCallback);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);
  mesh.onNodeTimeAdjusted(&nodeTimeAdjustedCallback);

  mesh.setContainsRoot(true);

  userScheduler.addTask( taskSendMessage );
  taskSendMessage.enable();
}

void loop() {
  mesh.update();
}
