#include "io.h"

#include <driver/gpio.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "board.h"

namespace io {

static const int PINS[COUNT] = {SWITCH_PIN, BOOT_BTN_PIN};

static TaskHandle_t task;
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
static State state[COUNT];
static volatile bool burst[COUNT];
static volatile int64_t burstStart[COUNT], lastEdge[COUNT];
static uint32_t debounce = 20000;
static bool ledOn = false;
static Callback callback = nullptr;

static void IRAM_ATTR edgeIsr(void *arg) {
  int i = (int)(intptr_t)arg;
  int64_t now = esp_timer_get_time();
  if (!burst[i]) {
    burst[i] = true;
    burstStart[i] = now;
  }
  lastEdge[i] = now;
  BaseType_t woken = pdFALSE;
  vTaskNotifyGiveFromISR(task, &woken);
  portYIELD_FROM_ISR(woken);
}

static void ioTask(void *) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    // 等所有输入的抖动平息
    for (;;) {
      bool pending = false;
      int64_t now = esp_timer_get_time();
      for (int i = 0; i < COUNT; i++) {
        if (!burst[i]) continue;
        if (now - lastEdge[i] < debounce) {
          pending = true;
          continue;
        }
        bool active = gpio_get_level((gpio_num_t)PINS[i]) == 0;
        int64_t t = burstStart[i];
        burst[i] = false;
        if (active == state[i].active) continue;  // 抖了一下又回到原状态
        taskENTER_CRITICAL(&mux);
        state[i].active = active;
        state[i].count++;
        state[i].changedUs = t;
        State s = state[i];
        taskEXIT_CRITICAL(&mux);
        if (callback) callback((Input)i, s);
      }
      if (!pending) break;
      vTaskDelay(1);
    }
  }
}

void begin() {
  gpio_config_t cfg = {};
  cfg.pin_bit_mask = (1ull << SWITCH_PIN) | (1ull << BOOT_BTN_PIN);
  cfg.mode = GPIO_MODE_INPUT;
  cfg.pull_up_en = GPIO_PULLUP_ENABLE;
  cfg.intr_type = GPIO_INTR_ANYEDGE;
  gpio_config(&cfg);

  gpio_config_t led = {};
  led.pin_bit_mask = 1ull << LED_PIN;
  led.mode = GPIO_MODE_OUTPUT;
  gpio_config(&led);
  setLed(false);

  int64_t now = esp_timer_get_time();
  for (int i = 0; i < COUNT; i++) state[i] = {gpio_get_level((gpio_num_t)PINS[i]) == 0, 0, (uint64_t)now};

  xTaskCreate(ioTask, "io", 3072, nullptr, 6, &task);
  gpio_install_isr_service(0);
  for (int i = 0; i < COUNT; i++) gpio_isr_handler_add((gpio_num_t)PINS[i], edgeIsr, (void *)(intptr_t)i);
}

State get(Input in) {
  taskENTER_CRITICAL(&mux);
  State s = state[in];
  taskEXIT_CRITICAL(&mux);
  return s;
}

void setDebounceUs(uint32_t us) { debounce = us; }
uint32_t debounceUs() { return debounce; }

void setLed(bool on) {
  ledOn = on;
  gpio_set_level((gpio_num_t)LED_PIN, on ? 0 : 1);
}
bool led() { return ledOn; }

void onChange(Callback cb) { callback = cb; }

}  // namespace io
