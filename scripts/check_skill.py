"""Show the three levels of the skill and how big each one is."""

from pathlib import Path

from google.adk.skills import load_skill_from_dir

ROOT = Path(__file__).resolve().parents[1]
skill = load_skill_from_dir(ROOT / "skills" / "ga4-context")  # also validates name and frontmatter

fm = skill.frontmatter
print(f"Level 1, always in the prompt:    name + description = {len(fm.name) + len(fm.description)} characters")
print(f"Level 2, when the skill is loaded: SKILL.md body      = {len(skill.instructions)} characters")
for name, text in skill.resources.references.items():
    print(f"Level 3, only if asked for:        references/{name} = {len(text)} characters")
print("For comparison, lesson 3's lookup_context result was about 36,700 characters, sent twice.")
