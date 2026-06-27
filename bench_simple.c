#include "raylib.h"
#include "raymath.h"
#include <stdio.h>
#include <math.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>

/* --- dynamic array runtime --- */
typedef struct { float   *data; int size; int capacity; } vector;
typedef struct { Vector2 *data; int size; int capacity; } vector_v2;
typedef struct { Vector3 *data; int size; int capacity; } vector_v3;
static vector* create(int init) {
    vector *v = (vector*)malloc(sizeof(vector));
    v->data = (float*)malloc((init > 0 ? init : 4) * sizeof(float));
    v->size = 0; v->capacity = (init > 0 ? init : 4);
    return v;
}
static void push(vector *v, float val) {
    if (v->size >= v->capacity) {
        v->capacity *= 2;
        v->data = (float*)realloc(v->data, v->capacity * sizeof(float));
    }
    v->data[v->size++] = val;
}
static float get(vector *v, int i) {
    return (i >= 0 && i < v->size) ? v->data[i] : 0.0f;
}
static vector_v2* create_v2(int init) {
    vector_v2 *v = (vector_v2*)malloc(sizeof(vector_v2));
    v->data = (Vector2*)malloc((init > 0 ? init : 4) * sizeof(Vector2));
    v->size = 0; v->capacity = (init > 0 ? init : 4);
    return v;
}
static void push_v2(vector_v2 *v, Vector2 val) {
    if (v->size >= v->capacity) {
        v->capacity *= 2;
        v->data = (Vector2*)realloc(v->data, v->capacity * sizeof(Vector2));
    }
    v->data[v->size++] = val;
}
static Vector2 get_v2(vector_v2 *v, int i) {
    return (i >= 0 && i < v->size) ? v->data[i] : (Vector2){0};
}
static vector_v3* create_v3(int init) {
    vector_v3 *v = (vector_v3*)malloc(sizeof(vector_v3));
    v->data = (Vector3*)malloc((init > 0 ? init : 4) * sizeof(Vector3));
    v->size = 0; v->capacity = (init > 0 ? init : 4);
    return v;
}
static void push_v3(vector_v3 *v, Vector3 val) {
    if (v->size >= v->capacity) {
        v->capacity *= 2;
        v->data = (Vector3*)realloc(v->data, v->capacity * sizeof(Vector3));
    }
    v->data[v->size++] = val;
}
static Vector3 get_v3(vector_v3 *v, int i) {
    return (i >= 0 && i < v->size) ? v->data[i] : (Vector3){0};
}
/* ------------------------------ */

#define WIDTH    100
#define HEIGHT   100
#define FPS      60

static int key_from_name(const char *name) {
    if (strcmp(name, "SPACE") == 0)    return KEY_SPACE;
    if (strcmp(name, "ENTER") == 0)    return KEY_ENTER;
    if (strcmp(name, "LEFT") == 0)     return KEY_LEFT;
    if (strcmp(name, "RIGHT") == 0)    return KEY_RIGHT;
    if (strcmp(name, "UP") == 0)       return KEY_UP;
    if (strcmp(name, "DOWN") == 0)     return KEY_DOWN;
    if (strcmp(name, "ESCAPE") == 0)   return KEY_ESCAPE;
    if (strlen(name) == 1 && name[0] >= 'A' && name[0] <= 'Z')
        return KEY_A + (name[0] - 'A');
    if (strlen(name) == 1 && name[0] >= '0' && name[0] <= '9')
        return KEY_ZERO + (name[0] - '0');
    return KEY_NULL;
}

char *to_string(float f) {
    char *buf = malloc(32);
    sprintf(buf, "%g", f);
    return buf;
}

vector* range(int start, int end) {
    vector* arr = create(end - start > 0 ? end - start : 4);
    for (int i = start; i < end; i++) {
        push(arr, (float)i);
    }
    return arr;
}

static int _lumen_perm[512];
static int _lumen_noise_ready = 0;
static void _lumen_noise_init(void) {
    int p[256]; for (int i=0;i<256;i++) p[i]=i;
    unsigned int s=12345;
    for (int i=255;i>0;i--) { s=s*1664525u+1013904223u; int j=(int)((s>>16)%(i+1)); int t=p[i];p[i]=p[j];p[j]=t; }
    for (int i=0;i<512;i++) _lumen_perm[i]=p[i&255];
    _lumen_noise_ready=1;
}
static float _lumen_fade(float t){return t*t*t*(t*(t*6-15)+10);}
static float _lumen_lerpf(float a,float b,float t){return a+t*(b-a);}
static float _lumen_grad2(int h,float x,float y){switch(h&3){case 0:return x+y;case 1:return -x+y;case 2:return x-y;case 3:return -x-y;}return 0;}
static float lumen_noise2(float x,float y){
    if(!_lumen_noise_ready)_lumen_noise_init();
    int xi=(int)floorf(x)&255,yi=(int)floorf(y)&255;
    float xf=x-floorf(x),yf=y-floorf(y);
    float u=_lumen_fade(xf),v=_lumen_fade(yf);
    int aa=_lumen_perm[_lumen_perm[xi]+yi],ab=_lumen_perm[_lumen_perm[xi]+yi+1];
    int ba=_lumen_perm[_lumen_perm[xi+1]+yi],bb=_lumen_perm[_lumen_perm[xi+1]+yi+1];
    return _lumen_lerpf(_lumen_lerpf(_lumen_grad2(aa,xf,yf),_lumen_grad2(ba,xf-1,yf),u),
                        _lumen_lerpf(_lumen_grad2(ab,xf,yf-1),_lumen_grad2(bb,xf-1,yf-1),u),v);
}
static float lumen_noise(float x){return lumen_noise2(x,0.0f);}


int main(void) {
    SetTraceLogLevel(LOG_NONE);
    InitWindow(WIDTH, HEIGHT, "Lumen");
    SetTargetFPS(FPS);
    float sim_time = 0.0f;

    while (!WindowShouldClose()) {
        float dt = GetFrameTime();
        sim_time += dt;
        BeginDrawing();
        ClearBackground((Color){ 15, 15, 25, 255 });
        DrawCircle((int)(((Vector2){ 50.0f, 50.0f }).x), (int)(((Vector2){ 50.0f, 50.0f }).y), 20.0f, (Color){ 255, 255, 255, 255 });
        EndDrawing();
    }

    CloseWindow();
    return 0;
}