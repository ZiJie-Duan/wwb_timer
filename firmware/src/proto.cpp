#include "proto.h"

namespace proto {

uint16_t crc16(const uint8_t *data, size_t len) {
  static uint16_t table[256];
  static bool ready = false;
  if (!ready) {
    for (int i = 0; i < 256; i++) {
      uint16_t c = i << 8;
      for (int b = 0; b < 8; b++) c = (c & 0x8000) ? (c << 1) ^ 0x1021 : c << 1;
      table[i] = c;
    }
    ready = true;
  }
  uint16_t crc = 0xFFFF;
  while (len--) crc = (crc << 8) ^ table[(crc >> 8) ^ *data++];
  return crc;
}

size_t cobsEncode(const uint8_t *in, size_t len, uint8_t *out) {
  size_t codeIdx = 0, o = 1;
  uint8_t code = 1;
  for (size_t i = 0; i < len; i++) {
    if (in[i] == 0) {
      out[codeIdx] = code;
      codeIdx = o++;
      code = 1;
    } else {
      out[o++] = in[i];
      if (++code == 0xFF) {
        out[codeIdx] = code;
        codeIdx = o++;
        code = 1;
      }
    }
  }
  out[codeIdx] = code;
  return o;
}

size_t cobsDecode(uint8_t *buf, size_t len) {
  size_t i = 0, o = 0;
  while (i < len) {
    uint8_t code = buf[i++];
    if (code == 0 || i + code - 1 > len) return 0;
    for (uint8_t k = 1; k < code; k++) buf[o++] = buf[i++];
    if (code != 0xFF && i < len) buf[o++] = 0;
  }
  return o;
}

}  // namespace proto
