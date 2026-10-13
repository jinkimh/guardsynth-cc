// Enumerate the declared Cartesian product; no oracle-based case selection.
#include <cassert>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include "formula_oracle.hpp"
#include "frozen_targets.hpp"

std::vector<Event> alphabet(int k, bool boundary, bool first) {
  std::vector<std::array<int,2>> links{{0,0}};
  if (boundary && !first) {
    for (int a=1; a<=4; ++a)
      if (k==1) links.push_back({a,0});
      else for (int b=1; b<=4; ++b) links.push_back({a,b});
  }
  std::vector<Event> result;
  for (int action=0; action<4; ++action)
    for (int create=-1; create<k; ++create)
      for (int pre=-1; pre<=(boundary ? -1 : 1); ++pre)
        for (int a=-1; a<=1; ++a)
          for (int b=-1; b<=(k==1 ? -1 : 1); ++b)
            for (auto link: links) result.push_back({action,create,pre,{a,b},link});
  return result;
}

template<class T> Snapshot execute(const std::vector<Event>& events, int k) {
  T target(k);
  for (int i=0; i<int(events.size()); ++i) {
    const auto& e=events[i];
    target.actions[i]=e.action==3 ? 0 : e.action; // YIELD aliases non-GO STOP in this IR.
    target.creates[i]=e.create;
    target.preconditions[i]=e.pre;
    for (int o=0; o<k; ++o) {
      target.observations[i*k+o]=e.obs[o];
      target.carry[i*k+o]=e.link[o]==0 ? 2 : e.link[o]==3 ? 0 : e.link[o]==4 ? -1 : 1;
      target.persist[i*k+o]=e.link[o]==2;
    }
  }
  for (int i=0; i<int(events.size()); ++i) { target.step(); target.idx++; }
  Snapshot s;
  s.bad=target.bad; s.missing=target.missing;
  s.first_bad=target.first_bad_idx; s.first_missing=target.first_missing_idx;
  s.bad_oid=target.first_bad_obligation; s.missing_oid=target.first_missing_obligation;
  for (int o=0; o<k; ++o) { s.active[o]=target.active[o]; s.known[o]=target.known[o]; s.linked[o]=target.linked[o]; }
  return s;
}

int verdict(const Snapshot& s) { return s.bad ? 0 : s.missing ? 1 : 2; }
bool issues_equal(const Snapshot& a, const Snapshot& b) {
  return a.bad==b.bad && a.missing==b.missing && a.first_bad==b.first_bad &&
    a.first_missing==b.first_missing && a.bad_oid==b.bad_oid && a.missing_oid==b.missing_oid;
}
bool states_equal(const Snapshot& a, const Snapshot& b, int k, bool boundary) {
  for (int o=0; o<k; ++o)
    if (a.active[o]!=b.active[o] || a.known[o]!=b.known[o] || (boundary && a.linked[o]!=b.linked[o])) return false;
  return true;
}
void print_snapshot(std::ostream& out, const Snapshot& s) {
  out << "{\"bad\":" << s.bad << ",\"missing\":" << s.missing
      << ",\"first_bad\":" << s.first_bad << ",\"first_missing\":" << s.first_missing
      << ",\"bad_oid\":" << s.bad_oid << ",\"missing_oid\":" << s.missing_oid
      << ",\"active\":[" << s.active[0] << ',' << s.active[1] << "]"
      << ",\"known\":[" << s.known[0] << ',' << s.known[1] << "]"
      << ",\"linked\":[" << s.linked[0] << ',' << s.linked[1] << "]}";
}

template<class T> void evaluate(const std::string& name, int k, int maximum, bool boundary, std::ofstream& failures) {
  auto first=alphabet(k,boundary,true), next=alphabet(k,boundary,false);
  uint64_t total=0, mismatch=0, issue_mismatch=0, state_mismatch=0;
  std::array<uint64_t,3> counts{0,0,0};
  for (int length=1; length<=maximum; ++length) {
    uint64_t size=first.size();
    for (int i=1; i<length; ++i) size*=next.size();
    std::vector<Event> events(length);
    for (uint64_t ordinal=0; ordinal<size; ++ordinal) {
      uint64_t value=ordinal;
      for (int i=length-1; i>=0; --i) {
        const auto& choices=i==0 ? first : next;
        events[i]=choices[value % choices.size()]; value/=choices.size();
      }
      Snapshot expected=formula_oracle(events,k,boundary), actual=execute<T>(events,k);
      bool ie=issues_equal(expected,actual), se=states_equal(expected,actual,k,boundary);
      total++; counts[verdict(expected)]++;
      issue_mismatch+=!ie; state_mismatch+=!se;
      if (!ie || !se) {
        mismatch++;
        failures << "{\"profile\":\"" << name << "\",\"length\":" << length << ",\"ordinal\":" << ordinal << ",\"events\":[";
        for (int i=0; i<length; ++i) {
          auto e=events[i];
          if (i) failures << ',';
          failures << '[' << e.action << ',' << e.create << ',' << e.pre << ',' << e.obs[0] << ',' << e.obs[1] << ',' << e.link[0] << ',' << e.link[1] << ']';
        }
        failures << "],\"expected\":"; print_snapshot(failures,expected);
        failures << ",\"actual\":"; print_snapshot(failures,actual); failures << "}\n";
      }
    }
    std::cerr << name << " length=" << length << " tested=" << total << " mismatches=" << mismatch << '\n';
  }
  std::cout << "{\"profile\":\"" << name << "\",\"obligations\":" << k << ",\"maximum_length\":" << maximum
            << ",\"alphabet_first\":" << first.size() << ",\"alphabet_next\":" << next.size()
            << ",\"cases\":" << total << ",\"mismatches\":" << mismatch
            << ",\"issue_mismatches\":" << issue_mismatch << ",\"state_mismatches\":" << state_mismatch
            << ",\"expected_counts\":[" << counts[0] << ',' << counts[1] << ',' << counts[2] << "]}" << std::endl;
}

int main(int argc, char** argv) {
  if (argc!=3) return 2;
  // Analytic traces check the formula path without looking at target outputs.
  std::vector<Event> conflict{{0,0,-1,{0,-1},{0,0}},{2,-1,-1,{-1,-1},{0,0}}};
  assert(formula_oracle(conflict,1,false).bad);
  std::vector<Event> expired{{0,0,-1,{0,-1},{0,0}},{2,-1,-1,{-1,-1},{1,0}}};
  assert(formula_oracle(expired,1,true).missing && !formula_oracle(expired,1,true).bad);
  expired[1].link[0]=3;
  assert(!formula_oracle(expired,1,true).missing && !formula_oracle(expired,1,true).active[0]);
  std::ofstream failures(argv[1]), controls(argv[2]);
  evaluate<ConditionTarget>("condition-k1-n3",1,3,false,failures);
  evaluate<ConditionTarget>("condition-k2-n3",2,3,false,failures);
  evaluate<BoundaryTarget>("boundary-k1-n3",1,3,true,failures);
  evaluate<BoundaryTarget>("boundary-k2-n2",2,2,true,failures);
  evaluate<StickyConditionTarget>("p4-sticky-release-control",1,2,false,controls);
}
