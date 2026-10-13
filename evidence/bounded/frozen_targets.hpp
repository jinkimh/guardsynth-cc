// Exact frozen XML step functions; only declarations are wrapped for native execution.
struct ConditionTarget {
int K; int actions[3]{}, creates[3]{}, preconditions[3]{};
int observations[6]{},carry[6]{},persist[6]{};
bool active[2]{},linked[2]{}; int known[2]{-1,-1}; int idx=0,precondition=-1;
bool bad=false,missing=false,bad_hold=false,bad_pre=false;
int first_bad_idx=-1,first_missing_idx=-1,first_bad_obligation=-1,first_missing_obligation=-1;
ConditionTarget(int k):K(k){}
void step() {
  int j;
  if (creates[idx] >= 0) active[creates[idx]] = true;
  if (preconditions[idx] >= 0) precondition = preconditions[idx];
  for (j = 0; j < K; j++) {
    if (observations[idx*K+j] >= 0) known[j] = observations[idx*K+j];
    if (active[j] && known[j] == 1) active[j] = false;
  }
  if (actions[idx] == 2) {
    if (precondition == 0) {
      bad = true; bad_pre = true;
      if (first_bad_idx < 0) { first_bad_idx = idx; first_bad_obligation = -2; }
    }
    for (j = 0; j < K; j++) {
      if (active[j] && known[j] == 0) {
        bad = true; bad_hold = true;
        if (first_bad_idx < 0) { first_bad_idx = idx; first_bad_obligation = j; }
      }
      if (active[j] && known[j] == -1) {
        missing = true;
        if (first_missing_idx < 0) { first_missing_idx = idx; first_missing_obligation = j; }
      }
    }
  }
}

};
struct BoundaryTarget {
int K; int actions[3]{}, creates[3]{}, preconditions[3]{};
int observations[6]{},carry[6]{},persist[6]{};
bool active[2]{},linked[2]{}; int known[2]{-1,-1}; int idx=0,precondition=-1;
bool bad=false,missing=false,bad_hold=false,bad_pre=false;
int first_bad_idx=-1,first_missing_idx=-1,first_bad_obligation=-1,first_missing_obligation=-1;
BoundaryTarget(int k):K(k){}
void step() {
  int j; int p;
  for (j=0; j<K; j++) {
    p=idx*K+j;
    if (carry[p] != 2) {
      linked[j]=(carry[p] == 1);
      if (carry[p] == 0) active[j]=false;
      if (carry[p] != 1 || persist[p] == 0) known[j]=-1;
    }
  }
  if (creates[idx] >= 0) {
    active[creates[idx]]=true;
    linked[creates[idx]]=true;
    known[creates[idx]]=-1;
  }
  for (j=0; j<K; j++) {
    p=idx*K+j;
    if (linked[j] && observations[p] >= 0) known[j]=observations[p];
    if (active[j] && linked[j] && known[j] == 1) active[j]=false;
  }
  if (actions[idx] == 2) {
    for (j=0; j<K; j++) {
      if (active[j] && linked[j] && known[j] == 0) {
        bad=true;
        if (first_bad_idx < 0) { first_bad_idx=idx; first_bad_obligation=j; }
      }
      if (active[j] && (!linked[j] || known[j] == -1)) {
        missing=true;
        if (first_missing_idx < 0) { first_missing_idx=idx; first_missing_obligation=j; }
      }
    }
  }
}
};
struct StickyConditionTarget {
int K; int actions[3]{}, creates[3]{}, preconditions[3]{};
int observations[6]{},carry[6]{},persist[6]{};
bool active[2]{},linked[2]{}; int known[2]{-1,-1}; int idx=0,precondition=-1;
bool bad=false,missing=false,bad_hold=false,bad_pre=false;
int first_bad_idx=-1,first_missing_idx=-1,first_bad_obligation=-1,first_missing_obligation=-1;
StickyConditionTarget(int k):K(k){}
void step() {
  int j;
  if (creates[idx] >= 0) active[creates[idx]] = true;
  if (preconditions[idx] >= 0) precondition = preconditions[idx];
  for (j = 0; j < K; j++) {
    if (observations[idx*K+j] >= 0) known[j] = observations[idx*K+j];
    if (active[j] && known[j] == 1) active[j] = true;
  }
  if (actions[idx] == 2) {
    if (precondition == 0) {
      bad = true; bad_pre = true;
      if (first_bad_idx < 0) { first_bad_idx = idx; first_bad_obligation = -2; }
    }
    for (j = 0; j < K; j++) {
      if (active[j] && known[j] == 0) {
        bad = true; bad_hold = true;
        if (first_bad_idx < 0) { first_bad_idx = idx; first_bad_obligation = j; }
      }
      if (active[j] && known[j] == -1) {
        missing = true;
        if (first_missing_idx < 0) { first_missing_idx = idx; first_missing_obligation = j; }
      }
    }
  }
}

};
