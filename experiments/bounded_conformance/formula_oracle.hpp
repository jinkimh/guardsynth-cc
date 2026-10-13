// Prefix formulas over the full trace. No monitor state or step() is used.
#pragma once
#include <array>
#include <vector>

struct Event {
  int action, create, pre;
  std::array<int, 2> obs, link;
};
struct Snapshot {
  bool bad=false, missing=false;
  int first_bad=-1, first_missing=-1, bad_oid=-1, missing_oid=-1;
  std::array<int, 2> active{0,0}, known{-1,-1}, linked{0,0};
};

inline bool linked_at(const std::vector<Event>& e, int i, int o) {
  for (int h=i; h>=0; --h) {
    if (e[h].create==o) return true;
    if (e[h].link[o]) return e[h].link[o]==1 || e[h].link[o]==2;
  }
  return false;
}

inline int known_at(const std::vector<Event>& e, int i, int o, bool boundary) {
  int lower=0;
  if (boundary) {
    for (int h=i; h>=0; --h) {
      // Creation and all boundary policies except explicitly persistent VERIFIED reset evidence.
      if (e[h].create==o || (e[h].link[o] && e[h].link[o]!=2)) { lower=h; break; }
    }
  }
  for (int h=i; h>=lower; --h)
    if (e[h].obs[o]>=0 && (!boundary || linked_at(e,h,o))) return e[h].obs[o];
  return -1;
}

inline bool active_at(const std::vector<Event>& e, int i, int o, bool boundary) {
  int creation=-1;
  for (int h=i; h>=0; --h) if (e[h].create==o) { creation=h; break; }
  if (creation<0) return false;
  for (int h=creation; h<=i; ++h) {
    if (boundary && h>creation && e[h].link[o]==3) return false;
    if (known_at(e,h,o,boundary)==1 && (!boundary || linked_at(e,h,o))) return false;
  }
  return true;
}

inline Snapshot formula_oracle(const std::vector<Event>& e, int k, bool boundary) {
  Snapshot s;
  for (int i=0; i<int(e.size()); ++i) {
    if (e[i].action!=2) continue;
    int p=-1;
    if (!boundary) for (int h=i; h>=0; --h) if (e[h].pre>=0) { p=e[h].pre; break; }
    if (p==0) {
      s.bad=true;
      if (s.first_bad<0) { s.first_bad=i; s.bad_oid=-2; }
    }
    for (int o=0; o<k; ++o) {
      if (!active_at(e,i,o,boundary)) continue;
      int q=known_at(e,i,o,boundary);
      bool linked=!boundary || linked_at(e,i,o);
      if (linked && q==0) {
        s.bad=true;
        if (s.first_bad<0) { s.first_bad=i; s.bad_oid=o; }
      }
      if (!linked || q==-1) {
        s.missing=true;
        if (s.first_missing<0) { s.first_missing=i; s.missing_oid=o; }
      }
    }
  }
  int last=int(e.size())-1;
  for (int o=0; o<k; ++o) {
    s.active[o]=active_at(e,last,o,boundary);
    s.known[o]=known_at(e,last,o,boundary);
    s.linked[o]=boundary && linked_at(e,last,o);
  }
  return s;
}
