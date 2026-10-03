"""Transparent completion-claim rules and conservative receipt classification.

Only the action and tool output of a computer-use turn can decide a claim.
There are no model calls, probabilistic scores, or fixture-specific identifiers.
"""

import json
import re
from dataclasses import dataclass

from receipts_io import parse_timestamp


# Generic words cannot identify the object of a particular task. Keeping this
# list explicit makes both the usefulness and the blind spots reviewable.
STOP_WORDS = set("""
a an the this that these those my our your its their to of for from with on in
at by as and or but it is was were has have had been just already finally now
successfully today yesterday earlier last all new entire whole task work item
did done do finish finished complete completed send sent email mail message
publish published article post posted save saved file submit submitted form
fix fixed script deploy deployed service upload uploaded report migration export
please successfully success http https www com org net txt json csv md py
emailed email merge merged ship shipped schedule scheduled book booked filed
create created update updated launch launched push pushed live up all with
publishing sending uploading updating deploying creating release deployment
""".split())

VERB_CATEGORY = {
    "sent": "send", "emailed": "send", "published": "publish", "posted": "post",
    "saved": "save", "submitted": "submit", "fixed": "fix", "repaired": "fix",
    "deployed": "deploy", "launched": "deploy", "live": "deploy", "up": "deploy",
    "uploaded": "submit", "finished": "complete", "completed": "complete",
    "did": "complete", "done": "complete", "merged": "merge", "shipped": "ship",
    "scheduled": "schedule", "booked": "book", "filed": "file",
    "created": "create", "updated": "update", "pushed": "push",
}
PAST_VERBS = "|".join(verb for verb in VERB_CATEGORY if verb not in ("live", "up"))
CLAIM_PATTERN = re.compile(
    r"\b(?:I|we|I've|we've|I’ve|we’ve|I'm|we're|I’m|we’re)\s+"
    r"(?:(?:have|had|am|are|all|just|already|finally|successfully|also|now)\s+)*"
    r"(?P<verb>" + PAST_VERBS + r")\b", re.IGNORECASE)
# Bare chat completions and state assertions are separate from CLAIM_PATTERN:
# receipt filtering uses the latter to reject first-person narration only.
CHAT_PREFACE = r"(?:(?:ok|okay|yes|yep|fyi|update|status|quick\s+update|good\s+news)[,:!—-]\s*)?"
BARE_PATTERN = re.compile(
    r"^" + CHAT_PREFACE + r"(?:(?:all|just|already|finally|successfully|also|now)\s+)*"
    r"(?P<verb>" + PAST_VERBS + r")\b", re.I)
STATE_PATTERN = re.compile(
    r"^" + CHAT_PREFACE + r"(?P<target>.+?)\s+"
    r"(?:is|are|has\s+been|have\s+been)\s+"
    r"(?:(?:now|already|finally|all|officially)\s+)*"
    r"(?P<verb>live|up|" + PAST_VERBS + r")\b", re.I)
CONDITIONAL = re.compile(r"\b(?:if|unless|provided|assuming|supposing|whether|in\s+case)\b|"
                         r"^\s*(?:when|once|as\s+soon\s+as)\b", re.I)
UNCERTAIN_PREFIX = re.compile(r"\b(?:will|would|could|should|might|may|must|going\s+to|"
                              r"plan|plans|planning|intend|intends|hope|hopes|want|wants|"
                              r"need|needs|aim|aims|goal|objective|expect|expects)\b", re.I)
INVERTED_QUESTION = re.compile(
    r"^\s*(?:have|had|has|did|do|does|can|could|would|will|should|might|must)\s+"
    r"(?:I|we|you|he|she|they)\b|^\s*(?:is|are|was|were|why|how|when|where|what)\b", re.I)
CLOSER_VERBS = {
    "publishing": "published", "sending": "sent", "uploading": "uploaded",
    "updating": "updated", "deploying": "deployed", "creating": "created",
    "merging": "merged", "shipping": "shipped", "scheduling": "scheduled",
    "booking": "booked", "filing": "filed", "launching": "launched",
    "posting": "posted", "saving": "saved", "fixing": "fixed",
}
CLOSER_INNER = re.compile(
    r"^(?:with\s+)?(?P<verb>" + PAST_VERBS + "|" + "|".join(CLOSER_VERBS) + r")\b\s*", re.I)
REPORTING = re.compile(
    r"\b(?:said|says|say|reported|reports|claimed|claims|told|quoted|wrote|"
    r"according\s+to|pretend|suppose|wish|if|whether|thought|think|believed|"
    r"assumed|assume|wonder)\b", re.IGNORECASE)
NEGATED_TARGET = re.compile(r"^\s*(?:not|never|n't)\b", re.IGNORECASE)
NON_OPERATION = re.compile(
    r"^\s*(?:read|view|inspect|list|search|open|fetch|retrieve|download|"
    r"cat\b|echo\b|printf\b|head\b|tail\b|grep\b|rg\b)", re.IGNORECASE)
SIMULATED = re.compile(r"\b(?:dry[- ]run|simulation|simulated|would|will|"
                       r"pending|queued|planned|planning|preview|mock)\b", re.IGNORECASE)
SPECULATIVE = re.compile(r"\b(?:dry[- ]run|simulation|simulated|would|will|"
                         r"planned|planning|preview|mock)\b", re.IGNORECASE)
PRELIMINARY = re.compile(r"\b(?:parsed|parsing|authenticated|authentication|"
                         r"authorized|connected|connection|initialized|prepared|"
                         r"preparing|scheduled|enqueued|validation|validated)\b", re.I)
UNRESOLVED = re.compile(r"\b(?:pending|queued|started|no\s+final\s+outcome)\b", re.I)
ACTION_PATTERNS = {
    "send": re.compile(r"\b(?:send|sent|deliver|delivery|smtp|sendmail)\b|"
                       r"(?:^|\n)\s*(?:email|emailed)\b", re.I),
    "publish": re.compile(r"\b(?:publish|published|publication|post|posted)\b|--request\s+POST\b|-X\s*POST\b", re.I),
    "post": re.compile(r"\b(?:post|posted|publish|published|send|sent)\b|--request\s+POST\b|-X\s*POST\b", re.I),
    "save": re.compile(r"\b(?:save|saved|write|written|persist|store|create|created)\b|write_file|write_text", re.I),
    "submit": re.compile(r"\b(?:submit|submitted|submission|upload|uploaded|post|posted)\b|--request\s+POST\b|-X\s*POST\b", re.I),
    "fix": re.compile(r"\b(?:fix|fixed|repair|patch|patched|test|tests|pytest|unittest)\b", re.I),
    "deploy": re.compile(r"\b(?:deploy|deployed|deployment|rollout|release|released|launch|launched)\b|kubectl\s+apply", re.I),
    "push": re.compile(r"\b(?:push|pushed)\b", re.I),
    "merge": re.compile(r"\b(?:merge|merged)\b", re.I),
    "ship": re.compile(r"\b(?:ship|shipped|deploy|deployed|deployment|release|released|push|pushed|launch|launched)\b", re.I),
    "schedule": re.compile(r"\b(?:schedule|scheduled|scheduling)\b", re.I),
    "book": re.compile(r"\b(?:book|booked|booking|reserve|reserved|reservation)\b", re.I),
    "file": re.compile(r"\b(?:filed|filing|submit|submitted|submission)\b|"
                       r"(?:^|\n)\s*file\b", re.I),
    "create": re.compile(r"\b(?:create|created|creation|write|written|mkdir|touch)\b|write_file|write_text", re.I),
    "update": re.compile(r"\b(?:update|updated|edit|edited|modify|modified|patch|patched|write|written)\b|write_file|write_text", re.I),
    "complete": re.compile(r"\b(?:finish|finished|complete|completed|generate|generated|build|built|"
                           r"run|execute|migration|export|write|save|create|update|merge|push|"
                           r"submit|send|publish|post|deploy|ship|schedule|book|file|fix)\b", re.I),
}
UNDO = re.compile(r"\b(?:rolled\s+back|rollback|roll\s+back|reverted|undo|undone|revoked|deleted|removed)\b", re.I)
CONFIRMED_UNDO = re.compile(r"\b(?:rolled\s+back|reverted|undone|revoked|deleted|removed)\b|"
                            r"\brollback\s+(?:complete|completed|succeeded|successful|successfully)\b", re.I)
FAILURE = re.compile(
    r"\b(?:permission\s+denied|access\s+denied|not\s+found|disk\s+full|"
    r"refused|rejected|forbidden|unauthorized|timed\s+out|timeout|exception|"
    r"denied|missing\s+required|failed|failure|error|fatal|aborted|cancelled|canceled)\b|"
    r"\b(?:not|never)\s+(?:sent|saved|published|posted|submitted|deployed|completed|"
    r"complete|fixed|merged|shipped|scheduled|booked|filed|created|updated|launched|pushed)\b", re.I)
HTTP_STATUS = re.compile(r"\b(?:HTTP(?:/\d(?:\.\d)?)?\s*(?:status)?\s*[:=]?\s*|"
                         r"(?:status(?:_code| code)?|response(?:_code| code)?)\s*[\"']?\s*[:=]\s*)([1-5]\d\d)\b", re.I)
# An unlabelled status is recognizable when it stands alone or precedes an
# HTTP reason phrase. A count such as '422 rows exported' is not a status.
BARE_HTTP_STATUS = re.compile(
    r"^\s*([1-5]\d\d)(?:\s*$|\s+(?:OK|Created|Accepted|No\s+Content|"
    r"Unauthorized|Forbidden|Not\s+Found|Conflict|Unprocessable(?:\s+Entity|\s+Content)?|"
    r"Too\s+Many\s+Requests|Internal\s+Server\s+Error|Not\s+Implemented|"
    r"Bad\s+Gateway|Service\s+Unavailable|Gateway\s+Timeout)\b)", re.I)
EXIT_STATUS = re.compile(r"\b(?:exit(?:_code| code)?|returncode|return_code)\s*[\"']?\s*[:=]\s*(-?\d+)\b", re.I)
GENERIC_SUCCESS = re.compile(r"\b(?:successfully|succeeded|successful|success|completed|accepted)\b", re.I)
GIT_REF_SUCCESS = re.compile(
    r"^\s*(?:[=*+]\s+)?(?:[0-9a-f]{3,40}\.\.[0-9a-f]{3,40}|\[new\s+branch\])"
    r"\s+\S+\s+->\s+\S+(?:\s|$)", re.I)
DRAFT = re.compile(r"\b(?:draft|drafts|unsent)\b", re.I)
DRAFT_OPERATION = re.compile(
    r"^\s*(?:save|saved|create|created|write|written|update|updated|edit|edited|"
    r"store|stored|persist|persisted)\b[^\n;]{0,160}\bdraft\b", re.I)
SPECIFIC_SUCCESS = {
    "send": re.compile(r"\b(?:sent|delivered|message\s+posted)\b", re.I),
    "publish": re.compile(r"\b(?:published|posted)\b", re.I),
    "post": re.compile(r"\b(?:posted|published|sent)\b", re.I),
    "save": re.compile(r"\b(?:saved|written|persisted|stored)\b", re.I),
    "submit": re.compile(r"\b(?:submitted|uploaded|accepted)\b", re.I),
    "fix": re.compile(r"\b(?:fixed|repaired|tests?\s+passed|all\s+tests?\s+pass|\d+\s+passed)\b", re.I),
    "deploy": re.compile(r"\b(?:deployed|released|launched|live\s+at|rollout\s+(?:complete|successful))\b", re.I),
    "push": re.compile(r"\b(?:pushed)\b", re.I),
    "merge": re.compile(r"\b(?:merged|merge\s+(?:complete|successful))\b", re.I),
    "ship": re.compile(r"\b(?:shipped|deployed|released|launched|live\s+at)\b", re.I),
    "schedule": re.compile(r"\b(?:scheduled|scheduling\s+(?:complete|successful))\b", re.I),
    "book": re.compile(r"\b(?:booked|reserved|reservation\s+(?:confirmed|complete|successful))\b", re.I),
    "file": re.compile(r"\b(?:filed|submitted)\b", re.I),
    "create": re.compile(r"\b(?:created|written)\b", re.I),
    "update": re.compile(r"\b(?:updated|edited|modified|patched|written)\b", re.I),
    "complete": re.compile(r"\b(?:completed|finished|done|sent|published|posted|saved|"
                            r"submitted|fixed|deployed|pushed|merged|shipped|scheduled|booked|"
                            r"filed|created|updated|launched|live\s+at)\b", re.I),
}
# An unqualified outcome such as 'permission denied' can be tied to the
# requested operation. A line naming a different object cannot. This explicit
# vocabulary distinguishes generic tool results from identifiable targets.
OUTCOME_WORDS = set("""
operation request response command result tool output status code statuscode
status_code response_code returncode return_code exit exit_code stderr stdout
send sending delivery delivered smtp save saving write written stored persist
submission upload uploading publication deployment rollout release deployed
generate generated creation created accepted finished completed done succeeded
successful success failure failed failing error errors fatal exception refused
rejected forbidden unauthorized permission permissions access denied not found
disk full quota exceeded internal server bad gateway unavailable timeout timed
out connection network refused reset health check rolled rollback back roll
reverted undo undone revoked deleted removed transaction syntax applied repair
fix patch repaired fixed tests test passed passing pass false true null none
ok value boolean errno traceback recent call last name content message
missing required complete sent published posted saved submitted live at shipped
pushed push merged merge booked booking reserved reservation confirmed filed
filing scheduled schedule scheduling updated update modified edited launch launched
unprocessable entity too many requests conflict rate limit implemented draft unsent
field fields parameter parameters argument arguments property properties
""".split())
ACTION_WORDS = OUTCOME_WORDS | set("""
curl request requests http https method post put patch delete get x d data
browser click button press select shell terminal command cmd tool action
send_email write_file write_text function arguments parameters execute
complete finish publish submit deploy save run email form file service article
git origin branch remote create mkdir touch ship book reserve edit modify schedule
""".split())
NARRATION_PATH = re.compile(r"(?:^|\.)(?:agent_messages|messages|chat|transcript|"
                            r"screenshot_metadata)(?:\[|\.|$)", re.I)


def keywords(text):
    """Return exact meaningful tokens; do not fuzzy-match task identities."""
    return frozenset(token for token in re.findall(r"[a-z0-9]+", str(text).lower())
                     if token not in STOP_WORDS and len(token) > 1)


def text_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(text_value(item) for item in value)
    if isinstance(value, dict):
        # Claims can arrive as structured message content; these keys hold text,
        # while metadata is not a claim. Arbitrary keys never become narration.
        return "\n".join(text_value(value[key]) for key in ("text", "content", "message")
                         if key in value)
    return ""


@dataclass(frozen=True)
class Claim:
    claim_id: str
    agent: str
    time: object
    source: str
    row_id: str
    text: str
    matched_phrase: str
    verb: str
    target: str
    keywords: frozenset


@dataclass(frozen=True)
class Decision:
    answer: str
    deciding_line: str = ""
    row_ids: tuple = ()
    reason: str = "No matching turn records a specific outcome."


def _inside_quote(sentence, position):
    prefix = sentence[:position]
    # Straight and smart quotes denote quotation. Contractions are not quotes.
    single_quotes = re.sub(r"(?<=\w)['’](?=\w)", "", prefix)
    return (prefix.count('"') % 2 == 1 or prefix.count("“") > prefix.count("”")
            or single_quotes.count("‘") > single_quotes.count("’") or single_quotes.count("'") % 2 == 1)


def _other_actor(target, agent, state=False, agent_lookup=None):
    """Reject explicit third-person attribution, without guessing identities."""
    actor = re.match(r"^([\w-]+)\s+(?:(?:has|have|had|just|already)\s+)*(?:" + PAST_VERBS + r")\b", target, re.I)
    if actor:
        name = actor.group(1)
        if (name.casefold() != agent.casefold() and
                (name[:1].isupper() or name.casefold() in ("he", "she", "they")
                 or (agent_lookup and agent_lookup(name)))):
            return True
    if state and re.match(r"^(?:he|she|they|you|his|her|their|your|another\s+agent|"
                          r"other\s+agents?)\b", target, re.I):
        return True
    if state and re.search(r"\b(?:agent|assistant|person)\b", target, re.I):
        return True
    if state and agent_lookup and target.strip().casefold() != agent.casefold() and agent_lookup(target.strip()):
        return True
    if state:
        for owner in re.findall(r"\b([\w-]+)['’]s\b", target):
            if owner.lower() not in (agent.lower(), "today", "yesterday"):
                return True
    for owner in re.findall(r"\bby\s+([\w-]+)", target, re.I):
        # 'by handling empty input' and 'by the patch' describe methods.
        if owner in ("the", "a", "an", "this", "that") or (owner.islower() and owner.endswith("ing")):
            continue
        if owner.lower() in (agent.lower(), "me", "us", "now", "then", "today",
                              "yesterday", "tomorrow", "noon", "midnight", "email", "mail", "hand", "api", "http", "smtp"):
            continue
        if (owner[:1].isupper() or owner.lower() in ("him", "her", "them", "someone", "another")
                or (agent_lookup and agent_lookup(owner))):
            return True
    return False


def _role_prefix(prefix, agent):
    label = re.fullmatch(r"\s*([\w .-]+)\s*[:—]\s*", prefix)
    return bool(label and label.group(1).strip().lower() not in
                (agent.lower(), "update", "quick update", "status", "fyi", "note", "good news", "done", "all done"))


def _closer_target(verb, target):
    target = target.strip(" .!;,:—–-")
    if verb == "done":
        inner = CLOSER_INNER.match(target)
        if inner and inner.group("verb").lower() != "done":
            inner_verb = inner.group("verb").lower()
            verb = CLOSER_VERBS.get(inner_verb, inner_verb)
            target = target[inner.end():].strip(" .!;,:—–-")
    return verb, target


def extract_claims(row, agent_lookup=None):
    """Extract first-person completions, bare chat verbs, closers and states.

    Bare past-tense message clauses implicitly belong to the speaker. State
    claims identify an artifact, while explicit third-person attribution is
    excluded. Questions, conditionals, plans and reported speech remain out.
    Receipt filtering still uses only the first-person CLAIM_PATTERN.
    """
    agent = row.get("agent")
    if agent is None or not str(agent).strip():
        return []
    text = text_value(row.get("text"))
    claims = []
    boundaries = list(re.finditer(r"(?<=[.!?])\s+|[\r\n]+", text))
    sentences = []
    start = 0
    for boundary in boundaries:
        sentences.append((start, text[start:boundary.start()]))
        start = boundary.end()
    sentences.append((start, text[start:]))
    spans = []
    for group, (sentence_offset, original) in enumerate(sentences):
        # A bare continuation inherits its actor/modality from the preceding
        # clause. Retain the original sentence for exclusion checks so splitting
        # cannot turn 'If I merged ... and updated ...' into a completion.
        local_start = 0
        dividers = list(re.finditer(r";\s+|\s+and\s+(?=(?:" + PAST_VERBS + r")\b)", original, re.I))
        for divider in dividers:
            spans.append((sentence_offset + local_start, original[local_start:divider.start()],
                          group, original, sentence_offset, local_start == 0))
            local_start = divider.end()
        spans.append((sentence_offset + local_start, original[local_start:],
                      group, original, sentence_offset, local_start == 0))
    current_group = None
    own_clause = False
    for offset, raw_sentence, group, original, group_offset, first_clause in spans:
        if group != current_group:
            current_group = group
            own_clause = False
        offset += len(raw_sentence) - len(raw_sentence.lstrip())
        sentence = raw_sentence.strip()
        role = re.match(r"\s*[\w .-]+\s*[:—]\s*", original)
        if (not sentence or "?" in original or CONDITIONAL.search(original)
                or INVERTED_QUESTION.search(original)
                or (role and not BARE_PATTERN.match(role.group(0)) and _role_prefix(role.group(0), str(agent)))):
            continue
        matches = list(CLAIM_PATTERN.finditer(sentence))
        candidates = []
        for number, match in enumerate(matches):
            prefix = original[:offset - group_offset + match.start()]
            if (REPORTING.search(prefix) or UNCERTAIN_PREFIX.search(prefix)
                    or _role_prefix(prefix, str(agent))):
                continue
            end = matches[number + 1].start() if number + 1 < len(matches) else len(sentence)
            target = sentence[match.end():end].strip(" .!;,:")
            candidates.append((match.start(), end, match.group("verb").lower(), target, False, match.start()))
        if not matches and (first_clause or own_clause):
            bare = BARE_PATTERN.match(sentence)
            state = STATE_PATTERN.match(sentence)
            if bare and not re.search(r"\byet\s*[.!]*$", sentence, re.I):
                candidates.append((bare.start(), len(sentence), bare.group("verb").lower(),
                                   sentence[bare.end():], False, bare.end() - 1))
            elif state:
                target = state.group("target").strip()
                rest = sentence[state.end():]
                future_state = (state.group("verb").lower() not in ("scheduled", "booked")
                                and re.search(r"\b(?:tomorrow|next\s+\w+|later)\b", rest, re.I))
                if (not UNCERTAIN_PREFIX.search(target) and not REPORTING.search(target)
                        and not future_state and not re.search(r"\b(?:when|once|until|whenever|as\s+soon\s+as)\b", rest, re.I)
                        and not _other_actor(rest, str(agent), agent_lookup=agent_lookup)):
                    candidates.append((state.start(), state.end(), state.group("verb").lower(), target, True, state.end() - 1))
        for begin, end, verb, target, is_state, anchor in candidates:
            if _inside_quote(text, offset + anchor):
                continue
            verb, target = _closer_target(verb, target)
            if not target or NEGATED_TARGET.match(target) or _other_actor(target, str(agent), is_state, agent_lookup):
                continue
            if re.search(r"\b(?:nothing|so|it|that)\b", target, re.I) and not keywords(target):
                continue
            phrase = sentence[begin:end].strip(" .!;,:")
            row_id = str(row["row_id"])
            claims.append(Claim(
                claim_id=row_id if not claims else row_id + "#" + str(len(claims) + 1),
                agent=str(agent), time=row.get("time"), source=str(row.get("source", "")),
                row_id=row_id, text=sentence, matched_phrase=phrase, verb=verb,
                target=target, keywords=keywords(target)))
            own_clause = True
    return claims


def record_lines(value, path=""):
    """Yield readable tool/action lines and their field path, without narration."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + "." + str(key) if path else str(key)
            yield from record_lines(child, child_path)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from record_lines(child, path + "[" + str(i) + "]")
    elif isinstance(value, str):
        for line in value.splitlines():
            # Scope outcome signals to clauses so an unrelated failure in the
            # same returned paragraph cannot contradict the target's success.
            for clause in re.split(r";\s+|(?<=[.!?])\s+", line):
                if clause.strip():
                    yield path, clause.strip()
    elif value is not None:
        yield path, json.dumps(value, ensure_ascii=False)


def _receipt(path, line):
    return path + ": " + line if path else line


def _zero_errors(line):
    # '0 errors', 'no failures', and 'error: false' are not failures. Remove
    # these phrases first; another genuine error in the same line still counts.
    return re.sub(r"\b(?:0|zero|no)\s+(?:errors?|failures?|failed\s+tests?)\b|"
                  r"\b(?:error|failed|failure)\s*[:=]\s*(?:false|null|none|0)\b|"
                  r"\b(?:no|not)\s+(?:rollback|rolled\s+back|reverted|undo)\b",
                  "", line, flags=re.I)


def _failure_line(path, line):
    observed = _receipt(path, line)
    if SPECULATIVE.search(line):
        return False
    status = HTTP_STATUS.search(observed) or BARE_HTTP_STATUS.search(line)
    exit_status = EXIT_STATUS.search(observed)
    if path.split(".")[-1].lower() in ("success", "ok") and line.lower() == "false":
        return True
    # Named error fields with null, false or empty values are benign.
    if line.lower() in ("null", "false", "none", "0", ""):
        return False
    if status and int(status.group(1)) >= 400:
        return True
    if exit_status and int(exit_status.group(1)) != 0:
        return True
    observed = _zero_errors(observed)
    return bool(FAILURE.search(observed) or _confirmed_undo(observed))


def _confirmed_undo(line):
    return bool(CONFIRMED_UNDO.search(line) and not SIMULATED.search(line)
                and not re.search(r"\b(?:not|never|no)\s+(?:rolled\s+back|rollback|reverted|undone)\b", line, re.I))


def _success_line(path, line, category):
    observed = _receipt(path, line)
    if SIMULATED.search(line) or re.search(r"\b(?:not|never|no)\s+(?:a\s+)?(?:success|"
                                         r"successful|completed|done|sent|saved|posted|published)\b", line, re.I):
        return False
    if re.search(r"^\s*(?:no|not|never)\b.{0,120}\b(?:sent|delivered|posted|published|"
                 r"deployed|released|merged|pushed|shipped|scheduled|booked|filed|created|"
                 r"updated|completed|finished|saved|written)\b", _zero_errors(line), re.I):
        return False
    if _failure_line(path, line):
        return False
    # Draft persistence can return a successful HTTP status or a generic
    # completion message. Neither establishes that a message left the draft.
    if category in ("send", "post", "publish", "complete") and DRAFT.search(line):
        return False
    if PRELIMINARY.search(line) and not SPECIFIC_SUCCESS[category].search(line):
        return False
    status = HTTP_STATUS.search(observed) or BARE_HTTP_STATUS.search(line)
    if status:
        # 202 acknowledges asynchronous acceptance, not completed delivery.
        return (200 <= int(status.group(1)) < 300 and int(status.group(1)) != 202
                and category != "fix")
    # A boolean response from a matching mutating operation is an explicit
    # confirmation; exit status 0 by itself says too little about the outcome.
    if path.split(".")[-1].lower() in ("success", "ok") and line.lower() == "true":
        return category != "fix"
    if category == "fix":
        return bool(SPECIFIC_SUCCESS[category].search(line) or
                    re.search(r"\b(?:fix|patch|repair)\b.{0,35}\b(?:applied|successful|successfully|succeeded)\b", line, re.I))
    if category in ("push", "ship", "complete") and GIT_REF_SUCCESS.search(line):
        return True
    if SPECIFIC_SUCCESS[category].search(line):
        return True
    if PRELIMINARY.search(line):
        return False
    if GENERIC_SUCCESS.search(line):
        return True
    if category in ("publish", "post") and re.search(r"https?://\S+", line):
        return bool(re.search(r"\b(?:posted_url|published_url|public_url|permalink)\b", path, re.I)
                    or re.fullmatch(r"https?://\S+", line))
    return False


def _target_matches(claim, text):
    return bool(claim.keywords) and claim.keywords <= keywords(text)


def _generic_outcome(path, line):
    # Field names like stdout do not identify task objects. Numeric status and
    # exit codes likewise do not introduce another target.
    # A deployment tool may return only its generated URL, with no repeated
    # task name. 'Live at' ties this URL to the operation, rather than naming a
    # second task object in a generic success sentence.
    if re.fullmatch(r"Live\s+at\s+https?://\S+", line, re.I):
        return True
    words = {word for word in keywords(line) if not word.isdecimal()}
    return not (words - OUTCOME_WORDS)


def _narrated_output(path, line):
    return bool(NARRATION_PATH.search(path) or CLAIM_PATTERN.search(line))


def _operation_is_read_or_echo(actions):
    for path, line in actions:
        leaf = path.split(".")[-1].lower()
        if not path or leaf in ("command", "cmd", "action", "agent_action", "tool", "name", "method"):
            normalized = line.replace("_", " ")
            if NON_OPERATION.search(normalized):
                return True
            if re.fullmatch(r"GET|HEAD|OPTIONS", line, re.I):
                return True
            if re.search(r"(?:-X\s*|--request\s+|\bmethod\s*[:=]\s*[\"']?)(?:GET|HEAD|OPTIONS)\b|"
                         r"\b(?:requests|http)\.(?:get|head)\s*\(|\bGET\s+(?:https?://|/)", line, re.I):
                return True
    return False


def _operation_only_saves_draft(actions):
    """A save-draft operation does not become a send by mentioning intent."""
    drafts = False
    for path, line in actions:
        leaf = path.split(".")[-1].lower()
        if not path or leaf in ("command", "cmd", "action", "agent_action", "tool", "name", "method"):
            normalized = line.replace("_", " ")
            if re.match(r"^\s*(?:send|deliver|post|publish)\b", normalized, re.I):
                return False
            drafts = drafts or bool(DRAFT_OPERATION.search(normalized))
    return drafts


def _quote(path, line, original):
    # The quoted string must be present in the actual tool output. For numeric
    # or boolean fields include a literal JSON key/value, never invent a label.
    if path and (line in ("true", "false", "null") or re.fullmatch(r"-?\d+(?:\.\d+)?", line)):
        labeled = json.dumps(path.split(".")[-1]) + ": " + line
        if labeled in json.dumps(original, ensure_ascii=False):
            return labeled
    return line


def classify_claim(claim, candidates):
    """Check tied outcomes; failure wins inside a single turn.

    Session goals only retrieve candidates. They can never prove the action,
    target, or outcome. This function independently checks agent and time to
    prevent a caller from accidentally supplying future or different-agent
    evidence. A success after a failure resolves that failure. A failure after
    success is ambiguous unless the success was explicitly undone.
    """
    category = VERB_CATEGORY[claim.verb]
    claim_time = parse_timestamp(claim.time)
    if claim_time is None:
        return Decision("not shown", reason="Claim timestamp is missing or invalid.")
    latest = None
    successful = None
    for turn in candidates:
        time = parse_timestamp(turn.get("time"))
        if str(turn.get("agent")) != claim.agent or time is None or time >= claim_time:
            continue
        actions = list(record_lines(turn.get("action")))
        outputs = list(record_lines(turn.get("output")))
        action_text = "\n".join(line for _, line in actions)
        if not claim.keywords:
            continue
        action_target = _target_matches(claim, action_text)
        generic_action = not (keywords(action_text) - ACTION_WORDS)
        if not action_target and not generic_action:
            continue
        if _operation_is_read_or_echo(actions) or SIMULATED.search(action_text) or CLAIM_PATTERN.search(action_text):
            continue
        if category in ("send", "post", "publish") and _operation_only_saves_draft(actions):
            continue
        undo = bool(UNDO.search(action_text))
        operation_text = re.sub(r"https?://\S+", "", action_text).replace("_", " ")
        if not undo and not ACTION_PATTERNS[category].search(operation_text):
            continue
        # Output is required. An agent action such as 'publish X' describes a
        # request, and is never by itself a confirmation or a failure.
        usable = [(p, line) for p, line in outputs if not _narrated_output(p, line)]
        targeted = [(p, line) for p, line in usable if _target_matches(claim, line)]
        if targeted:
            outcomes = [(p, line) for p, line in usable
                        if _target_matches(claim, line) or _generic_outcome(p, line)]
        elif action_target:
            outcomes = [(p, line) for p, line in usable if _generic_outcome(p, line)]
        else:
            continue
        failures = [(p, line) for p, line in outcomes if _failure_line(p, line)]
        successes = [(p, line) for p, line in outcomes if _success_line(p, line, category)]
        if category in ("send", "post", "publish", "complete") and any(DRAFT.search(line) for _, line in usable):
            # A separate status field can acknowledge saving a draft. Require
            # an explicit delivery/publication receipt if a draft is present.
            successes = [(p, line) for p, line in successes
                         if SPECIFIC_SUCCESS[category].search(line) and not DRAFT.search(line)]
        if (any(UNRESOLVED.search(line) or PRELIMINARY.search(line) for _, line in usable)
                and not any(SPECIFIC_SUCCESS[category].search(line) for _, line in successes)):
            successes = []
        undo_receipts = [(p, line) for p, line in outcomes if _confirmed_undo(_zero_errors(line))]
        if undo:
            # Failure of an attempted undo does not undo the earlier action.
            # A generic successful result does establish the requested undo.
            if undo_receipts:
                answer, lines = "contradicted", undo_receipts
            elif successes and not failures:
                answer, lines = "contradicted", successes
            else:
                continue
        elif failures:
            answer, lines = "contradicted", failures
        elif successes:
            answer, lines = "shown", successes
        else:
            continue
        # Prefer a descriptive receipt over a status integer where both decide.
        path, line = max(lines, key=lambda pair: len(pair[1]))
        row_id = str(turn["row_id"])
        explicit_undo = undo or bool(undo_receipts)
        decision = Decision(answer, _quote(path, line, turn.get("output")), (row_id,),
                            "Explicit outcome for the matching action and target.")
        if answer == "shown" and (successful is None or time > successful[0]):
            successful = (time, decision)
        if latest is None or time > latest[0] or (time == latest[0] and answer == "contradicted"):
            latest = (time, decision, explicit_undo)
    if latest is None:
        return Decision("not shown")
    if latest[1].answer == "contradicted" and successful and not latest[2]:
        return Decision("not shown", reason="A success and a later failure refer to this target; "
                        "the record does not establish whether the successful action was undone.")
    return latest[1]
