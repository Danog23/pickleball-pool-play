import streamlit as st
import pandas as pd
from collections import defaultdict

st.set_page_config(page_title="Pickleball Pool Play", layout="wide")
st.title("Pickleball Pool Play + Knockout")

# ---------- Password ----------
if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False
if "admin_password" not in st.session_state:
    st.session_state.admin_password = "2302"

# ---------- Helpers ----------
def snake_seed(players, num_pools):
    pools = [[] for _ in range(num_pools)]
    for i, p in enumerate(players):
        cycle = i // num_pools
        pos = i % num_pools
        if cycle % 2 == 0:
            pools[pos].append(p)
        else:
            pools[num_pools - 1 - pos].append(p)
    return pools

def decide_pools(n):
    if n <= 7:
        return 1
    return 2

def generate_round_robin(players):
    n = len(players)
    names = list(players)
    matches = []

    if n == 4:
        matches = [
            ((names[0], names[1]), (names[2], names[3])),
            ((names[0], names[2]), (names[1], names[3])),
            ((names[0], names[3]), (names[1], names[2])),
        ]
    elif n == 5:
        matches = [
            ((names[0], names[1]), (names[2], names[3])),
            ((names[1], names[2]), (names[3], names[4])),
            ((names[2], names[3]), (names[4], names[0])),
            ((names[3], names[4]), (names[0], names[1])),
            ((names[4], names[0]), (names[1], names[2])),
        ]
    elif n == 6:
        matches = [
            ((names[0], names[1]), (names[2], names[3])),
            ((names[0], names[2]), (names[4], names[5])),
            ((names[1], names[4]), (names[3], names[5])),
            ((names[0], names[3]), (names[1], names[5])),
            ((names[2], names[4]), (names[1], names[3])),
            ((names[0], names[5]), (names[2], names[4])),
        ]
    elif n >= 7:
        for i in range(n):
            sitting = names[i]
            playing = [names[j] for j in range(n) if j != i]
            matches.append(((playing[0], playing[1]), (playing[2], playing[3])))
    return matches

def calc_standings(pool_players, scores_dict, matches):
    diff = defaultdict(int)
    wins = defaultdict(int)

    for idx, match in enumerate(matches):
        key = f"m{idx}"
        if key not in scores_dict:
            continue
        s1, s2 = scores_dict[key]
        t1, t2 = match
        for p in t1:
            diff[p] += s1 - s2
        for p in t2:
            diff[p] += s2 - s1
        if s1 > s2:
            for p in t1:
                wins[p] += 1
        elif s2 > s1:
            for p in t2:
                wins[p] += 1

    ranking = [{"name": p, "diff": diff[p], "wins": wins[p]} for p in pool_players]
    ranking.sort(key=lambda x: (x["diff"], x["wins"]), reverse=True)
    return ranking

# ---------- Admin Login ----------
col1, col2 = st.columns([1, 5])
with col1:
    if not st.session_state.admin_unlocked:
        if st.button("Admin Mode"):
            st.session_state.show_login = True
    else:
        st.success("Admin Active")
        if st.button("User Mode"):
            st.session_state.admin_unlocked = False
            st.rerun()

if st.session_state.get("show_login") and not st.session_state.admin_unlocked:
    with st.form("login"):
        pwd = st.text_input("Admin Password", type="password")
        if st.form_submit_button("Login"):
            if pwd == st.session_state.admin_password:
                st.session_state.admin_unlocked = True
                st.session_state.show_login = False
                st.rerun()
            else:
                st.error("Wrong password")

st.markdown("---")

# ---------- Setup ----------
if "stage" not in st.session_state:
    st.session_state.stage = "setup"

if st.session_state.stage == "setup":
    st.header("Enter Players")
    
    if st.session_state.admin_unlocked:
        st.caption("Enter one name per line, strongest player first (Best → Worst).")
    else:
        st.caption("Enter one name per line.")

    default = """Alex
Jordan
Sam
Taylor
Casey
Riley
Morgan
Jamie"""
    player_text = st.text_area("Players", value=default, height=220)

    play_to = st.number_input("Play to", 7, 21, 11)

    if st.button("Create Pools & Schedule", type="primary"):
        players = [p.strip() for p in player_text.strip().splitlines() if p.strip()]
        if len(players) < 4:
            st.error("Need at least 4 players")
        else:
            num_pools = decide_pools(len(players))
            pools = snake_seed(players, num_pools)

            # Build full match list for all pools
            all_matches = []
            for p_idx, pool in enumerate(pools):
                matches = generate_round_robin(pool)
                for m_idx, match in enumerate(matches):
                    all_matches.append({
                        "pool_idx": p_idx,
                        "match_idx": m_idx,
                        "match": match,
                        "key": f"p{p_idx}_m{m_idx}"
                    })

            st.session_state.players = players
            st.session_state.pools = pools
            st.session_state.num_pools = num_pools
            st.session_state.play_to = play_to
            st.session_state.scores = {}
            st.session_state.locked = {}
            st.session_state.match_queue = all_matches
            st.session_state.current_match = all_matches[0] if all_matches else None
            st.session_state.stage = "pool_play"
            st.session_state.pool_standings = None
            st.session_state.semis = None
            st.session_state.final = None
            st.session_state.final_done = False
            st.rerun()

# ---------- Pool Play ----------
if st.session_state.stage == "pool_play":
    pools = st.session_state.pools
    play_to = st.session_state.play_to
    is_admin = st.session_state.admin_unlocked

    st.header("Pool Play")

    # Show pools
    cols = st.columns(len(pools))
    for i, pool in enumerate(pools):
        with cols[i]:
            st.subheader(f"Pool {chr(65+i)}")
            for j, p in enumerate(pool, 1):
                st.write(f"{j}. {p}")

    st.markdown("---")

    # Current match board
    current = st.session_state.get("current_match")
    if current:
        t1, t2 = current["match"]
        key = current["key"]
        pool_letter = chr(65 + current["pool_idx"])

        st.subheader(f"Current Match — Pool {pool_letter}")
        st.write(f"**{t1[0]} & {t1[1]}**  vs  **{t2[0]} & {t2[1]}**")

        if is_admin:
            locked = st.session_state.locked.get(key, False)
            if locked:
                s1, s2 = st.session_state.scores.get(key, (0, 0))
                st.write(f"Score: **{s1} – {s2}**")
                if st.button("🔓 Unlock to Edit"):
                    st.session_state.locked[key] = False
                    st.rerun()
            else:
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                with c1:
                    s1 = st.number_input("Score 1", 0, 30, st.session_state.scores.get(key, (play_to, play_to-1))[0], key=f"s1_{key}")
                with c2:
                    s2 = st.number_input("Score 2", 0, 30, st.session_state.scores.get(key, (play_to, play_to-1))[1], key=f"s2_{key}")
                with c3:
                    if st.button("Save & Next", type="primary"):
                        st.session_state.scores[key] = (s1, s2)
                        st.session_state.locked[key] = True
                        # Move to next match
                        queue = st.session_state.match_queue
                        if queue and queue[0]["key"] == key:
                            queue.pop(0)
                        st.session_state.current_match = queue[0] if queue else None
                        st.rerun()
                with c4:
                    if st.button("Skip →"):
                        queue = st.session_state.match_queue
                        if queue and queue[0]["key"] == key:
                            skipped = queue.pop(0)
                            queue.append(skipped)
                        st.session_state.current_match = queue[0] if queue else None
                        st.rerun()
        else:
            if key in st.session_state.scores:
                s1, s2 = st.session_state.scores[key]
                st.write(f"Score: **{s1} – {s2}**")
            else:
                st.info("Waiting for score...")
    else:
        st.success("All pool matches completed!")

        if is_admin:
            if st.button("Calculate Standings → Knockout", type="primary"):
                standings = []
                for p_idx, pool in enumerate(pools):
                    matches = generate_round_robin(pool)
                    pool_scores = {}
                    for m_idx in range(len(matches)):
                        key = f"p{p_idx}_m{m_idx}"
                        if key in st.session_state.scores:
                            pool_scores[f"m{m_idx}"] = st.session_state.scores[key]
                    ranking = calc_standings(pool, pool_scores, matches)
                    standings.append(ranking)

                st.session_state.pool_standings = standings

                if st.session_state.num_pools == 1:
                    r = standings[0]
                    if len(r) >= 4:
                        st.session_state.final = (
                            (r[0]["name"], r[1]["name"]),
                            (r[2]["name"], r[3]["name"])
                        )
                    st.session_state.stage = "final"
                else:
                    a = standings[0]
                    b = standings[1]
                    if len(a) >= 4 and len(b) >= 4:
                        st.session_state.semis = [
                            ((a[0]["name"], b[0]["name"]), (a[3]["name"], b[3]["name"])),
                            ((a[1]["name"], b[1]["name"]), (a[2]["name"], b[2]["name"]))
                        ]
                        st.session_state.semi_queue = [0, 1]
                        st.session_state.current_semi = 0
                    st.session_state.stage = "semis"
                st.rerun()

# ---------- Semi Finals ----------
if st.session_state.stage == "semis":
    st.header("Semi-Finals")
    is_admin = st.session_state.admin_unlocked
    play_to = st.session_state.play_to

    if st.session_state.pool_standings:
        cols = st.columns(2)
        for i, ranking in enumerate(st.session_state.pool_standings):
            with cols[i]:
                st.subheader(f"Pool {chr(65+i)} Standings")
                df = pd.DataFrame([{"#": j+1, "Player": r["name"], "+/−": r["diff"], "Wins": r["wins"]} for j, r in enumerate(ranking)])
                st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")

    current_semi = st.session_state.get("current_semi", 0)
    if current_semi < 2:
        match = st.session_state.semis[current_semi]
        t1, t2 = match
        key = f"semi_{current_semi}"

        st.subheader(f"Semi {current_semi + 1}")
        st.write(f"**{t1[0]} & {t1[1]}**  vs  **{t2[0]} & {t2[1]}**")

        if is_admin:
            locked = st.session_state.locked.get(key, False)
            if locked:
                s1, s2 = st.session_state.scores.get(key, (0, 0))
                st.write(f"Score: **{s1} – {s2}**")
                if st.button("🔓 Unlock Semi"):
                    st.session_state.locked[key] = False
                    st.rerun()
            else:
                c1, c2, c3 = st.columns(3)
                with c1:
                    s1 = st.number_input("Score 1", 0, 30, play_to, key=f"ss1_{current_semi}")
                with c2:
                    s2 = st.number_input("Score 2", 0, 30, play_to-1, key=f"ss2_{current_semi}")
                with c3:
                    if st.button("Save & Next Semi", type="primary"):
                        st.session_state.scores[key] = (s1, s2)
                        st.session_state.locked[key] = True
                        st.session_state.current_semi = current_semi + 1
                        st.rerun()
        else:
            if key in st.session_state.scores:
                s1, s2 = st.session_state.scores[key]
                st.write(f"Result: **{s1} – {s2}**")
    else:
        st.success("Both semi-finals completed!")
        if is_admin and st.button("Go to Final", type="primary"):
            winners = []
            for i in range(2):
                key = f"semi_{i}"
                s1, s2 = st.session_state.scores[key]
                t1, t2 = st.session_state.semis[i]
                winners.append(t1 if s1 > s2 else t2)
            st.session_state.final = (winners[0], winners[1])
            st.session_state.stage = "final"
            st.rerun()

# ---------- Final ----------
if st.session_state.stage == "final":
    st.header("FINAL")
    is_admin = st.session_state.admin_unlocked
    play_to = st.session_state.play_to

    if st.session_state.pool_standings:
        cols = st.columns(len(st.session_state.pool_standings))
        for i, ranking in enumerate(st.session_state.pool_standings):
            with cols[i]:
                st.markdown(f"**Pool {chr(65+i)} Standings**")
                df = pd.DataFrame([{"#": j+1, "Player": r["name"], "+/−": r["diff"], "Wins": r["wins"]} for j, r in enumerate(ranking)])
                st.dataframe(df, hide_index=True, use_container_width=True)

    t1, t2 = st.session_state.final
    st.markdown("---")
    st.subheader("Championship Match")
    st.write(f"**{t1[0]} & {t1[1]}**  vs  **{t2[0]} & {t2[1]}**")

    key = "final"
    if is_admin:
        locked = st.session_state.locked.get(key, False)
        if locked or st.session_state.get("final_done"):
            s1, s2 = st.session_state.scores.get(key, (0, 0))
            st.write(f"Score: **{s1} – {s2}**")
            if not st.session_state.get("final_done") and st.button("🔓 Unlock Final"):
                st.session_state.locked[key] = False
                st.rerun()
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                s1 = st.number_input("Score 1", 0, 30, play_to, key="fs1")
            with c2:
                s2 = st.number_input("Score 2", 0, 30, play_to-1, key="fs2")
            with c3:
                if st.button("Save Final Score", type="primary"):
                    st.session_state.scores[key] = (s1, s2)
                    st.session_state.locked[key] = True
                    st.session_state.final_done = True
                    st.rerun()
    else:
        if key in st.session_state.scores:
            s1, s2 = st.session_state.scores[key]
            st.write(f"Result: **{s1} – {s2}**")

    if st.session_state.get("final_done"):
        s1, s2 = st.session_state.scores["final"]
        winners = t1 if s1 > s2 else t2
        st.success(f"🏆 Champions: **{winners[0]} & {winners[1]}**")
        st.balloons()
        st.info("Winning team plays free!")

# ---------- Reset ----------
st.markdown("---")
if st.session_state.admin_unlocked:
    if st.button("Reset Everything (Start New Night)"):
        for key in list(st.session_state.keys()):
            if key not in ["admin_password", "admin_unlocked"]:
                del st.session_state[key]
        st.rerun()
