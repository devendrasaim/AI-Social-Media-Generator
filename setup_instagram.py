#!/usr/bin/env python3
"""
One-time Instagram session setup.
Run this once to authenticate and save a session file that main.py reuses.

Usage:
    python setup_instagram.py
"""
import os
import sys
import time
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired, TwoFactorRequired, BadCredentials,
    ChallengeError, ChallengeSelfieCaptcha,
)

load_dotenv()
USERNAME = os.getenv("INSTAGRAM_USERNAME")
PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

if not USERNAME or not PASSWORD:
    print("ERROR: INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env")
    sys.exit(1)

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instagram_session.json")


def challenge_code_handler(username, choice):
    """Called by instagrapi when it needs the 6-digit verification code."""
    from instagrapi.mixins.challenge import ChallengeChoice
    medium = "email" if choice == ChallengeChoice.EMAIL else "SMS/phone"
    print(f"\nInstagram sent a 6-digit code to your {medium}.")
    code = input("Enter the code: ").strip()
    return code


def _make_client():
    cl = Client()
    cl.delay_range = [2, 5]
    cl.challenge_code_handler = challenge_code_handler
    return cl


def _show_app_approval_instructions():
    print()
    print("=" * 55)
    print("  ACTION REQUIRED  (takes ~30 seconds)")
    print("=" * 55)
    print()
    print("Instagram needs you to approve this login via")
    print("the Instagram app on your phone:")
    print()
    print("  Option A - Notification:")
    print("    Look for a push notification saying")
    print("    'New login attempt detected'")
    print("    Tap it and select 'This was me'")
    print()
    print("  Option B - Login Activity:")
    print("    Instagram app > Profile > Menu (3 lines)")
    print("    > Settings > Security > Login Activity")
    print("    > find today's login > 'This was me'")
    print()
    print("  Option C - Email:")
    print("    Check the email linked to myaiguru9 for")
    print("    a verification code, then enter it above")
    print()
    input("Press Enter AFTER you have approved the login... ")
    print()


def _try_login(cl):
    try:
        cl.login(USERNAME, PASSWORD)
        return True, None
    except TwoFactorRequired:
        code = input("\n2FA is enabled. Enter your authenticator/SMS code: ").strip()
        cl.login(USERNAME, PASSWORD, verification_code=code)
        return True, None
    except ChallengeRequired as e:
        return False, e
    except BadCredentials:
        print("ERROR: Wrong username or password. Check your .env file.")
        sys.exit(1)
    except Exception as e:
        return False, e


def main():
    print("=" * 55)
    print("  Instagram Session Setup")
    print("=" * 55)
    print(f"Account : {USERNAME}")
    print()

    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
        print("Removed old session file.\n")

    cl = _make_client()

    # ── Attempt 1: clean login ───────────────────────────────
    print("Attempting login...")
    ok, err = _try_login(cl)
    if ok:
        print("Logged in on first attempt - no challenge needed.")
    else:
        # ── Resolve challenge, then wait for app approval ────
        print(f"Challenge required - resolving...")
        try:
            cl.challenge_resolve(cl.last_json)
        except (ChallengeRequired, ChallengeError, ChallengeSelfieCaptcha):
            pass  # fall through to manual approval prompt
        except Exception:
            pass

        _show_app_approval_instructions()

        # ── Retry login after app approval ──────────────────
        print("Retrying login...")
        time.sleep(3)
        cl = _make_client()
        ok2, err2 = _try_login(cl)

        if not ok2:
            # Second attempt with fresh credentials after longer wait
            print(f"Still failing ({err2}). Waiting 15 seconds and trying once more...")
            time.sleep(15)
            cl = _make_client()
            ok3, err3 = _try_login(cl)

            if not ok3:
                print(f"\nLogin failed: {err3}")
                print()
                print("The account may need manual unlock. Try:")
                print("  1. Log into instagram.com in a browser and complete any")
                print("     security check shown there.")
                print("  2. Wait 10-15 minutes, then run this script again.")
                sys.exit(1)

    # ── Verify session works ─────────────────────────────────
    print("Verifying session...")
    try:
        cl.get_timeline_feed()
        print("Session verified.")
    except Exception as e:
        print(f"Session verification failed: {e}")
        sys.exit(1)

    cl.dump_settings(SESSION_FILE)
    print(f"\nSession saved: {SESSION_FILE}")
    print("\nSetup complete. You can now run:")
    print("  python main.py --perplexity \"AI tools 2026\" --tone casual")
    print("=" * 55)


if __name__ == "__main__":
    main()
