# 용어 대장

목적은 정확한 번역어를 찾는 것이 아니라 **한 문서 안에서 흔들리지 않는 것**이다.

기본인 coding 프로필에서는 "번역하지 않는다" 목록 밖의 영어도 원문대로 둔다.
아래 "한국어로 쓴다" 표는 prose 프로필의 기준이다. 다만 `해당`처럼 한국어끼리의
직역 표현은 프로필과 상관없이 고친다.
팀이 이미 쓰는 말이 여기 없으면, 여기를 고치고 그 말을 쓴다.

## 번역하지 않는다

코드 심볼(함수·클래스·필드·파일명)은 언제나 백틱 안에 원문 그대로.

그 외 원문 유지: commit, branch, merge, rebase, cherry-pick, PR, issue,
cache, checkpoint, rollback, migration, schema, index, embedding, chunk,
workspace, workflow, node, edge, tool, agent, prompt, token, session,
sandbox, hook, middleware, endpoint, payload, timeout, retry, fallback,
handler, manifest, orphan, custom, CLI, side effect, idempotent.

## 새 우리말을 지어내지 않는다

억지로 옮긴 낯선 한국어는 원래 말보다 더 헷갈린다. 독자가 이미 아는 말이면 영어든
굳은 음차어든 그대로 둔다. 고칠 대상은 낱말이 아니라 한국어답지 않은 문장 구조다.

- 영어와 굳은 음차어는 둘 다 된다: `handler`·`핸들러`, `manifest`·`매니페스트`,
  `fallback`·`폴백`, `orphan`·`고아`, `idempotent`·`멱등`. 한 문서 안에서는 하나로 맞춘다.
- 팀이 쓰는 관용 표현도 둔다: `예외를 삼킨다`, `조용히 실패한다`.
- 지어낸 말은 쓰지 않는다: `주인 없는 객체`(orphan), `대체 경로`(fallback),
  `등록된 함수`(handler), `직접 짠 루틴`(custom).
- 고친 결과가 원래 말보다 길거나 처음 보는 말이면 되돌린다.

근거(2026-10-18, linkBrain-server 위키 241쪽): handler 186·핸들러 168, fallback 243·폴백 212·대체 경로 0,
orphan 51·고아 56·주인 없는 1, 조용히 194, 삼키/삼킨 29, 부작용 12·부수 효과 12·side effect 9.

## 한국어로 쓴다

| 영어 | 한국어 | 쓰지 말 것 |
|---|---|---|
| case | 경우 | 케이스 |
| the said / corresponding | 그 · 이 (또는 이름 직접) | 해당 |
| performance | 성능 | 퍼포먼스 |
| issue (problem) | 문제 | 이슈 (트래커 항목일 때만 issue) |
| trade-off | 절충 · 맞바꿈 | 트레이드오프 (문맥상 원문도 허용) |
| requirement | 요구사항 | 리콰이어먼트 |
| deprecated | 폐기 예정 | 디프리케이트 |
| edge case | 예외 상황 | 엣지 케이스 |
| validate | 검증한다 | 밸리데이션을 수행한다 | <!-- lint-skip -->

`issue`는 두 뜻이 겹친다. 문제를 뜻하면 "문제", Linear/GitHub 항목이면 "이슈".
한 문단에서 두 뜻을 섞지 않는다.

## 혼용 금지 쌍

같은 대상을 두 이름으로 부르지 않는다. 문서 첫머리에서 하나를 고르고 끝까지 간다.

- 워크스페이스 / workspace / 작업공간 → 하나만
- 에이전트 / agent → 하나만
- 사용자 / 유저 / user → 하나만
