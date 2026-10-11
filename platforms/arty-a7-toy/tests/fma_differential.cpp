#include "VFmaPrecisionCheck.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <vector>

struct Request {
  int tag, kind, op, rm;
  uint64_t a, b, c;
  bool random;
};

int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  VFmaPrecisionCheck dut;
  std::mt19937_64 rng(0xf00d531124ULL);
  std::deque<Request> pending;
  std::ofstream vectors("vectors.csv");
  std::array<uint64_t, 3> comparisons{};
  std::array<std::array<int, 2>, 3> saved{};
  uint64_t cycles = 0, resets = 0, dropped = 0;
  bool failed = false;
  auto tick = [&](bool valid, Request r, bool reset = false) {
    dut.clock = 0;
    dut.reset = reset;
    dut.valid = valid && !reset;
    dut.tag = r.tag;
    dut.kind = r.kind;
    dut.op = r.op;
    dut.rm = r.rm;
    dut.a = r.a; dut.b = r.b; dut.c = r.c;
    if (reset) { dropped += pending.size(); pending.clear(); }
    else if (valid) pending.push_back(r);
    dut.eval();
    dut.clock = 1;
    dut.eval();
    ++cycles;
    if (reset) return;
    if (!dut.equal) {
      std::cerr << "FAIL cycle=" << cycles << " expected=0x" << std::hex
                << dut.expected << " actual=0x" << dut.actual
                << " expectedFlags=" << unsigned(dut.expectedFlags)
                << " actualFlags=" << unsigned(dut.actualFlags) << std::dec << "\n";
      if (!pending.empty()) {
        auto x = pending.front();
        std::cerr << "tag=" << x.tag << " kind=" << x.kind << " op=" << x.op << " rm=" << x.rm
                  << " a=" << std::hex << x.a << " b=" << x.b << " c=" << x.c << std::dec << "\n";
      }
      failed = true;
      return;
    }
    if (dut.outValid) {
      if (pending.empty()) { std::cerr << "FAIL unexpected response\n"; failed = true; return; }
      auto x = pending.front(); pending.pop_front();
      auto n = ++comparisons[x.tag];
      int cohort = x.random ? 1 : 0;
      if (saved[x.tag][cohort] < 256 && n % (x.random ? 41 : 61) == 0) {
        vectors << x.tag << ',' << x.kind << ',' << x.op << ',' << x.rm << ',' << std::hex
                << x.a << ',' << x.b << ',' << x.c << ',' << dut.expected << ','
                << unsigned(dut.expectedFlags) << std::dec << '\n';
        ++saved[x.tag][cohort];
      }
    }
  };
  Request empty{};
  for (int i = 0; i < 8; ++i) tick(false, empty, true);
  for (int tag = 0; tag < 3 && !failed; ++tag) {
    int sig = tag == 0 ? 11 : tag == 1 ? 24 : 53;
    int exp = tag == 0 ? 5 : tag == 1 ? 8 : 11;
    int bits = sig + exp;
    uint64_t sign = uint64_t(1) << (bits - 1);
    uint64_t inf = ((uint64_t(1) << exp) - 1) << (sig - 1);
    uint64_t one = ((uint64_t(1) << (exp - 1)) - 1) << (sig - 1);
    uint64_t minNormal = uint64_t(1) << (sig - 1);
    std::vector<uint64_t> edge{
      0, sign, 1, sign | 1, minNormal - 1, sign | (minNormal - 1), minNormal, sign | minNormal,
      one, sign | one, one + 1, one - 1, one + (uint64_t(1) << (sig - 1)),
      one - (uint64_t(1) << (sig - 1)), inf - 1, sign | (inf - 1),
      inf, sign | inf, inf | (uint64_t(1) << (sig - 2)), inf | 1,
      sign | inf | (uint64_t(1) << (sig - 2)), sign | inf | 1
    };
    for (int rm = 0; rm < 5 && !failed; ++rm)
      for (int kind = 0; kind < 3 && !failed; ++kind)
        for (int op = 0; op < (kind == 0 ? 4 : kind == 1 ? 2 : 1) && !failed; ++op)
          for (size_t i = 0; i < edge.size() && !failed; ++i)
            for (size_t j = 0; j < edge.size() && !failed; ++j) {
              tick(true, {tag, kind, op, rm, edge[i], edge[j], edge[(i * 3 + j * 5) % edge.size()], false});
              if ((rng() & 15) == 0) tick(false, empty);
            }
    // Fusion cancellation: (1+ulp)*(1-ulp)-1 must retain its tiny exact residue.
    for (int rm = 0; rm < 5 && !failed; ++rm) {
      tick(true, {tag, 0, 0, rm, one + 1, one - 2, sign | one, false});
      tick(true, {tag, 0, 0, rm, inf - 1, one + (uint64_t(1) << (sig - 1)), 0, false});
    }
  }
  for (int i = 0; i < 200000 && !failed; ++i) {
    int tag = rng() % 3, kind = rng() % 3;
    int op = rng() % (kind == 0 ? 4 : kind == 1 ? 2 : 1);
    tick(true, {tag, kind, op, int(rng() % 5), rng(), rng(), rng(), true});
    if ((rng() & 7) == 0) tick(false, empty);
    if (i != 0 && i % 25000 == 0) {
      ++resets;
      for (int j = 0; j < 8; ++j) tick(false, empty, true);
    }
  }
  for (int i = 0; i < 12 && !failed; ++i) tick(false, empty);
  if (failed || !pending.empty()) return 1;
  vectors.close();
  dut.final();
  for (int tag = 0; tag < 3; ++tag) {
    if (saved[tag][0] != 256 || saved[tag][1] != 256) return 2;
  }
  std::cout << "PASS FMA_SHARED cycles=" << cycles << " comparisons="
            << comparisons[0] + comparisons[1] + comparisons[2]
            << " H=" << comparisons[0] << " S=" << comparisons[1] << " D=" << comparisons[2]
            << " resets=" << resets << " reset_discarded=" << dropped << " cpu_vectors=1536\n";
}
