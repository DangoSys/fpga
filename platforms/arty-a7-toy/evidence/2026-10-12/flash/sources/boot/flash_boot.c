// LZ4 block reader, bounds checks and CRC before jumping to unchanged OpenSBI.
#include <stdint.h>
#define REG8(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define FLASH_OFFSET 0x400000u
#define FLASH_AVAILABLE 0xc00000u
#define MAX_OUTPUT 0x0f000000u  // Exclude the top DDR region used for this stack.

static void text(const char *s) {
  while (*s) REG8(0x60020000) = (uint8_t)*s++;
}
static void hex(unsigned value) {
  static const char digits[]="0123456789abcdef";
  REG8(0x60020000)=digits[(value >> 4) & 15];
  REG8(0x60020000)=digits[value & 15];
}
static void fail(void) {
  REG8(0x6002000c) = 1;
  text("FAIL FLASH_BOOT\n");
  *(volatile uint64_t *)0x60000000 = 0xbad0f101;
  for (;;) __asm__ volatile("wfi");
}
static uint8_t spi(uint8_t value) {
  REG8(0x60020008) = value;
  unsigned timeout = 100000;
  while (REG8(0x60020009) & 1) if (!--timeout) fail();
  return REG8(0x60020008);
}
static uint32_t crc_byte(uint32_t crc, uint8_t value) {
  // Nibble lookup saves time without a 1 KiB CRC table in the boot ROM.
  static const uint32_t table[16] = {
    0x00000000,0x1db71064,0x3b6e20c8,0x26d930ac,
    0x76dc4190,0x6b6b51f4,0x4db26158,0x5005713c,
    0xedb88320,0xf00f9344,0xd6d6a3e8,0xcb61b38c,
    0x9b64c2b0,0x86d3d2d4,0xa00ae278,0xbdbdf21c
  };
  crc ^= value;
  crc = (crc >> 4) ^ table[crc & 15];
  return (crc >> 4) ^ table[crc & 15];
}
static uint8_t get(unsigned *remaining) {
  if (!*remaining) fail();
  --*remaining;
  return spi(0xff);
}
static unsigned length(unsigned initial, unsigned *remaining) {
  if (initial == 15) {
    unsigned more;
    do {
      more = get(remaining);
      if (initial > MAX_OUTPUT - more) fail();
      initial += more;
    } while (more == 255);
  }
  return initial;
}
static void launch(void) __attribute__((noreturn));
static void launch(void) {
  __asm__ volatile(
    "fence rw,rw\n fence.i\n csrr a0,mhartid\n li a1,0x11000\n"
    "li t0,0x1800\n csrs mstatus,t0\n li t0,0x80000000\n csrw mepc,t0\n mret\n"
    ::: "a0","a1","t0","memory");
  __builtin_unreachable();
}
void flash_main(void) {
  if (!REG8(0x6002000a)) launch();  // SW0 high: original UART load/RUN recovery.
  text("TOY FLASH_BOOT\n");
  // Exercise STARTUPE2 CCLK takeover with CS high before sending commands.
  REG8(0x6002000c) = 1;
  spi(0xff); spi(0xff);
  REG8(0x6002000c) = 0;
  spi(0x9f);
  unsigned manufacturer = spi(0xff), type = spi(0xff), capacity = spi(0xff);
  text("FLASH_ID ");hex(manufacturer);hex(type);hex(capacity);text("\n");
  REG8(0x6002000c) = 1;
  if (!((manufacturer == 0x01 && type == 0x20) ||
        (manufacturer == 0x20 && type == 0xba)) || capacity != 0x18) fail();
  REG8(0x6002000c) = 0;
  spi(0x03); spi(FLASH_OFFSET >> 16); spi(0); spi(0);
  uint32_t header[8];
  uint32_t hcrc = ~0u;
  for (unsigned i = 0; i < 8; ++i) {
    uint32_t word = 0;
    for (unsigned b = 0; b < 4; ++b) {
      uint8_t v = spi(0xff);
      word |= (uint32_t)v << (b * 8);
      if (i < 7) hcrc = crc_byte(hcrc, v);
    }
    header[i] = word;
  }
  if (header[0] != 0x46594f54 || header[1] != 0x00345a4c || header[2] != 1 ||
      !header[3] || header[3] > FLASH_AVAILABLE - 32 || !header[4] ||
      header[4] > MAX_OUTPUT || header[6] || header[7] != ~hcrc) fail();
  unsigned remaining = header[3], produced = 0;
  uint8_t *out = (uint8_t *)(uintptr_t)0x80000000;
  while (remaining) {
    unsigned token = get(&remaining);
    unsigned count = length(token >> 4, &remaining);
    if (count > remaining || count > header[4] - produced) fail();
    while (count--) out[produced++] = get(&remaining);
    if (!remaining) break;
    unsigned offset = get(&remaining);
    offset |= (unsigned)get(&remaining) << 8;
    count = length(token & 15, &remaining) + 4;
    if (!offset || offset > produced || count > header[4] - produced) fail();
    while (count--) { out[produced] = out[produced - offset]; ++produced; }
  }
  REG8(0x6002000c) = 1;
  if (produced != header[4]) fail();
  uint32_t crc = ~0u;
  for (unsigned i = 0; i < produced; ++i) crc = crc_byte(crc, out[i]);
  if (~crc != header[5]) fail();
  text("PASS FLASH_PAYLOAD_CRC\n");
  launch();
}
