; benchmark generated from python API
(set-info :status unknown)
(declare-fun supplied_temporal_release__clear_ms__const () Int)
(declare-fun supplied_temporal_release__entry_ms__const () Int)
(declare-fun supplied_temporal_release__enters__const () Bool)
(assert
 (let ((?x20 (+ supplied_temporal_release__clear_ms__const 500)))
 (=> supplied_temporal_release__enters__const (>= supplied_temporal_release__entry_ms__const ?x20))))
(assert
 (let ((?x20 (+ supplied_temporal_release__clear_ms__const 500)))
(and supplied_temporal_release__enters__const (< supplied_temporal_release__entry_ms__const ?x20))))
(check-sat)
