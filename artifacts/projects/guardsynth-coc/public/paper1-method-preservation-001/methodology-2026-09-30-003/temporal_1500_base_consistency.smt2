; benchmark generated from python API
(set-info :status unknown)
(declare-fun supplied_temporal_release__clear_ms__const () Int)
(declare-fun supplied_temporal_release__entry_ms__const () Int)
(declare-fun supplied_temporal_release__enters__const () Bool)
(assert
 (let (($x44 (>= supplied_temporal_release__entry_ms__const (+ supplied_temporal_release__clear_ms__const 1500))))
 (=> supplied_temporal_release__enters__const $x44)))
(check-sat)
