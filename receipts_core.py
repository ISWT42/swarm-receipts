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
""".split())

VERB_CATEGORY = {
    "sent": "send", "published": "publish", "posted": "post",
    "saved": "save", "submitted": "submit", "fixed": "fix",
    "deployed": "deploy", "uploaded": "submit", "finished": "complete",
    "completed": "complete", "did": "complete", "done": "complete",
}
CLAIM_PATTERN = re.compile(
    r"\b(?:I|we|I've|we've)\s+"
    r"(?:(?:have|had|just|already|finally|successfully|also|now)\s+)*"
    r"(?P<verb>sent|published|posted|saved|submitted|fixed|deployed|uploaded|"
    r"finished|completed|did|done)\b", re.IGNORECASE)
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
    "send": re.compile(r"\b(?:send|sent|deliver|delivery|smtp|sendmail)\b", re.I),
    "publish": re.compile(r"\b(?:publish|published|publication|post|posted)\b|--request\s+POST\b|-X\s*POST\b", re.I),
    "post": re.compile(r"\b(?:post|posted|publish|published|send|sent)\b|--request\s+POST\b|-X\s*POST\b", re.I),
    "save": re.compile(r"\b(?:save|saved|write|written|persist|store|create|created)\b|write_file|write_text", re.I),
    "submit": re.compile(r"\b(?:submit|submitted|submission|upload|uploaded|post|posted)\b|--request\s+POST\b|-X\s*POST\b", re.I),
    "fix": re.compile(r"\b(?:fix|fixed|repair|patch|patched|test|tests|pytest|unittest)\b", re.I),
    "deploy": re.compile(r"\b(?:deploy|deployed|deployment|rollout|release|released)\b|kubectl\s+apply", re.I),
    "complete": re.compile(r"\b(?:finish|finished|complete|completed|generate|generated|build|built|"
                           r"run|execute|migration|export|write|save|create)\b", re.I),
}
UNDO = re.compile(r"\b(?:rolled\s+back|rollback|roll\s+back|reverted|undo|undone|revoked|deleted|removed)\b", re.I)
CONFIRMED_UNDO = re.compile(r"\b(?:rolled\s+back|reverted|undone|revoked|deleted|removed)\b|"
                            r"\brollback\s+(?:complete|completed|succeeded|successful|successfully)\b", re.I)
FAILURE = re.compile(
    r"\b(?:permission\s+denied|access\s+denied|not\s+found|disk\s+full|"
    r"refused|rejected|forbidden|unauthorized|timed\s+out|timeout|exception|"
    r"failed|failure|error|fatal|aborted|cancelled|canceled)\b|"
    r"\b(?:not|never)\s+(?:sent|saved|published|posted|submitted|deployed|completed|fixed)\b", re.I)
HTTP_STATUS = re.compile(r"\b(?:HTTP(?:/\d(?:\.\d)?)?\s*(?:status)?\s*[:=]?\s*|"
                         r"(?:status(?:_code| code)?|response(?:_code| code)?)\s*[\"']?\s*[:=]\s*)([1-5]\d\d)\b", re.I)
EXIT_STATUS = re.compile(r"\b(?:exit(?:_code| code)?|returncode|return_code)\s*[\"']?\s*[:=]\s*(-?\d+)\b", re.I)
GENERIC_SUCCESS = re.compile(r"\b(?:successfully|succeeded|successful|success|completed|accepted)\b", re.I)
SPECIFIC_SUCCESS = {
    "send": re.compile(r"\b(?:sent|delivered)\b", re.I),
    "publish": re.compile(r"\b(?:published|posted)\b", re.I),
    "post": re.compile(r"\b(?:posted|published|sent)\b", re.I),
    "save": re.compile(r"\b(?:saved|written|persisted|stored)\b", re.I),
    "submit": re.compile(r"\b(?:submitted|uploaded|accepted)\b", re.I),
    "fix": re.compile(r"\b(?:fixed|repaired|tests?\s+passed|all\s+tests?\s+pass|\d+\s+passed)\b", re.I),
    "deploy": re.compile(r"\b(?:deployed|released|rollout\s+(?:complete|successful))\b", re.I),
    "complete": re.compile(r"\b(?:completed|finished|done)\b", re.I),
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
""".split())
ACTION_WORDS = OUTCOME_WORDS | set("""
curl request requests http https method post put patch delete get x d data
browser click button press select shell terminal command cmd tool action
send_email write_file write_text function arguments parameters execute
complete finish publish submit deploy save run email form file service article
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
    single_quotes = re.sub(r"(?<=\w)'(?=\w)", "", prefix)
    return (prefix.count('"') % 2 == 1 or prefix.count("“") > prefix.count("”")
            or prefix.count("‘") > prefix.count("’") or single_quotes.count("'") % 2 == 1)


def extract_claims(row):
    """Extract explicit first-person past completions from chat or memory.

    Questions, conditional statements, reported speech, negative claims and
    future statements are deliberately left out. One sentence can contain
    several explicit 'I ...' completions; each keeps its own phrase and id.
    """
    agent = row.get("agent")
    if agent is None or not str(agent).strip():
        return []
    text = text_value(row.get("text"))
    claims = []
    boundaries = list(re.finditer(r"(?<=[.!?])\s+|[\r\n]+", text))
    spans = []
    start = 0
    for boundary in boundaries:
        spans.append((start, text[start:boundary.start()]))
        start = boundary.end()
    spans.append((start, text[start:]))
    for offset, raw_sentence in spans:
        offset += len(raw_sentence) - len(raw_sentence.lstrip())
        sentence = raw_sentence.strip()
        if not sentence or "?" in sentence:
            continue
        matches = list(CLAIM_PATTERN.finditer(sentence))
        for number, match in enumerate(matches):
            prefix = sentence[:match.start()]
            if _inside_quote(text, offset + match.start()) or REPORTING.search(prefix):
                continue
            end = matches[number + 1].start() if number + 1 < len(matches) else len(sentence)
            target = sentence[match.end():end].strip(" .!;,:")
            if not target or NEGATED_TARGET.match(target):
                continue
            if re.search(r"\b(?:nothing|so|it|that)\b", target, re.I) and not keywords(target):
                continue
            phrase = sentence[match.start():end].strip(" .!;,:")
            verb = match.group("verb").lower()
            row_id = str(row["row_id"])
            claims.append(Claim(
                claim_id=row_id if not claims else row_id + "#" + str(len(claims) + 1),
                agent=str(agent), time=row.get("time"), source=str(row.get("source", "")),
                row_id=row_id, text=sentence, matched_phrase=phrase, verb=verb,
                target=target, keywords=keywords(target)))
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
    status = HTTP_STATUS.search(observed)
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
    if _failure_line(path, line):
        return False
    if PRELIMINARY.search(line) and not SPECIFIC_SUCCESS[category].search(line):
        return False
    status = HTTP_STATUS.search(observed)
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
