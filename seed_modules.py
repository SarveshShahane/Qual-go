import asyncio
import os
import re
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import select, delete
from app.database.sql.db import AsyncSessionService, engine
from app.database.sql.models.user import User
from app.database.sql.models.course import Module, Chapter, Topic, UserTopicProgress

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = Path(os.getenv("MODULES_DIR", str(WORKSPACE_ROOT / "modules")))


def format_title_from_slug(slug: str) -> str:
    # Example: "01-vectors" -> "01. Vectors"
    # "01-classical-bit-vs-qubit" -> "01. Classical Bit Vs Qubit"
    match = re.match(r"^(\d+)-(.*)$", slug)
    if match:
        num, rest = match.groups()
        words = rest.replace("-", " ").title()
        return f"{num}. {words}"
    return slug.replace("-", " ").title()


async def seed_directory_module(
    session,
    mod_dir: Path,
    mod_id: str,
    mod_name: str,
    mod_order: int,
    prefix: str,
):
    """Dynamically scan and seed a module from a directory containing chapter subfolders."""
    if not mod_dir.exists():
        print(f"Warning: Directory {mod_dir} does not exist!")
        return

    mod = Module(
        id=mod_id,
        name=mod_name,
        order=mod_order,
    )
    session.add(mod)
    await session.flush()
    print(f"\n=========================================================")
    print(f"Created module: {mod.name} (id: {mod.id})")
    print(f"=========================================================")

    chapter_dirs = sorted([d for d in mod_dir.iterdir() if d.is_dir()])
    for chap_idx, chap_dir in enumerate(chapter_dirs, start=1):
        chap_slug = chap_dir.name
        chap_id = f"chap_{prefix}_{chap_slug.replace('-', '_')}"
        chap_name = format_title_from_slug(chap_slug)

        chapter = Chapter(
            id=chap_id,
            module_id=mod.id,
            name=chap_name,
            order=chap_idx,
        )
        session.add(chapter)
        await session.flush()
        print(f"  -> Chapter {chap_idx}: {chap_name} (id: {chap_id})")

        topic_specs = []
        is_quiz_chap = "quiz" in chap_slug or "assessment" in chap_slug

        if (chap_dir / "README.md").exists():
            topic_specs.append({
                "id": f"top_{prefix}_{chap_slug[:2]}_overview",
                "name": "Quiz Overview & Instructions" if is_quiz_chap else "Overview & Key Takeaways",
                "file": "README.md",
            })
        if (chap_dir / "theory.md").exists():
            topic_specs.append({
                "id": f"top_{prefix}_{chap_slug[:2]}_theory",
                "name": "Theory & Worked Examples",
                "file": "theory.md",
            })
        if (chap_dir / "questions.md").exists():
            topic_specs.append({
                "id": f"top_{prefix}_{chap_slug[:2]}_questions",
                "name": "Mastery Quiz Problems" if is_quiz_chap else "Practice Questions",
                "file": "questions.md",
            })
        if (chap_dir / "answers.md").exists():
            topic_specs.append({
                "id": f"top_{prefix}_{chap_slug[:2]}_answers",
                "name": "Answer Key & Scoring Guide" if is_quiz_chap else "Solutions & Explanations",
                "file": "answers.md",
            })

        for top_order, spec in enumerate(topic_specs, start=1):
            file_path = chap_dir / spec["file"]
            content = file_path.read_text(encoding="utf-8")
            rel_path = f"modules/{mod_dir.name}/{chap_slug}/{spec['file']}"

            # Determine question type
            if is_quiz_chap:
                if spec["file"] in ["questions.md", "answers.md"]:
                    q_type = "mcq"
                else:
                    q_type = "reading"
            elif spec["file"] == "questions.md":
                # Detect if questions file has MCQ options (e.g., - **A.** or A.)
                if re.search(r"-\s*\*\*A\.\*\*|\bA\.\s+", content):
                    q_type = "mcq"
                else:
                    q_type = "code"
            elif spec["file"] == "answers.md":
                q_type = "reading"
            else:
                q_type = "reading"

            topic = Topic(
                id=spec["id"],
                chapter_id=chapter.id,
                name=spec["name"],
                content=content,
                content_path=rel_path,
                order=top_order,
                question_type=q_type,
            )
            session.add(topic)
            print(f"     • Topic {top_order}: {spec['name']} [type: {q_type}] ({len(content)} chars)")


async def seed():
    print(f"Loading modules from: {MODULES_DIR}")
    if not MODULES_DIR.exists():
        print(f"Error: {MODULES_DIR} does not exist!")
        return

    async with AsyncSessionService() as session:
        # Check existing modules to avoid duplicates
        existing_res = await session.execute(select(Module))
        existing_mods = existing_res.scalars().all()
        for mod in existing_mods:
            print(f"Removing old module: {mod.id} - {mod.name}")
            await session.delete(mod)
        await session.commit()

        # =========================================================
        # 1. Module 1: The Mathematics You Need (modules/Mathematics)
        # =========================================================
        await seed_directory_module(
            session=session,
            mod_dir=MODULES_DIR / "Mathematics",
            mod_id="mod_mathematics",
            mod_name="Module 1: The Mathematics You Need",
            mod_order=1,
            prefix="math",
        )

        # =========================================================
        # 2. Module 2: Qubits & State Representation (modules/Qubits)
        # =========================================================
        await seed_directory_module(
            session=session,
            mod_dir=MODULES_DIR / "Qubits",
            mod_id="mod_qubits",
            mod_name="Module 2: Qubits & State Representation",
            mod_order=2,
            prefix="qubits",
        )

        # =========================================================
        # 3. Module 3: Superposition & Measurement (modules/Superposition)
        # =========================================================
        await seed_directory_module(
            session=session,
            mod_dir=MODULES_DIR / "Superposition",
            mod_id="mod_superposition",
            mod_name="Module 3: Superposition & Measurement",
            mod_order=3,
            prefix="superpos",
        )

        # =========================================================
        # 4. Roadmap Modules (Future curriculum)
        # =========================================================
        roadmap_modules = [
            {
                "id": "mod_algorithms",
                "name": "Module 4: Standard Quantum Algorithms",
                "order": 4,
                "chapters": [
                    {
                        "slug": "01_deutsch_jozsa",
                        "name": "01. Deutsch-Jozsa & Quantum Parallelism",
                        "content": "# Deutsch-Jozsa Algorithm\n\nThe first algorithm demonstrating provable exponential quantum speedup over deterministic classical algorithms for black-box oracles.\n\nEvaluates whether a function $f: \\{0, 1\\}^n \\to \\{0, 1\\}$ is constant or balanced in a single query.",
                    },
                    {
                        "slug": "02_grover_search",
                        "name": "02. Grover's Unstructured Search",
                        "content": "# Grover's Unstructured Search Algorithm\n\nProvides a quadratic speedup for searching an unsorted database of $N$ elements in $\\mathcal{O}(\\sqrt{N})$ queries using amplitude amplification.\n\nKey steps:\n1. Equal superposition initialization\n2. Oracle phase inversion\n3. Diffusion operator (inversion about the mean)",
                    },
                ],
            },
            {
                "id": "mod_hardware",
                "name": "Module 5: Noise & Quantum Hardware",
                "order": 5,
                "chapters": [
                    {
                        "slug": "01_decoherence",
                        "name": "01. Decoherence & Relaxation Times",
                        "content": "# Decoherence & Relaxation Times (T1, T2)\n\nReal quantum hardware interacts with its environment, leading to energy loss ($T_1$ relaxation) and phase dephasing ($T_2$ coherence decay).\n\nUnderstanding noise models is essential for quantum error mitigation.",
                    },
                ],
            },
        ]

        print(f"\n=========================================================")
        print("Seeding Roadmap Modules...")
        print(f"=========================================================")
        for r_mod in roadmap_modules:
            mod_obj = Module(
                id=r_mod["id"],
                name=r_mod["name"],
                order=r_mod["order"],
            )
            session.add(mod_obj)
            await session.flush()
            print(f"Created roadmap module: {mod_obj.name} (id: {mod_obj.id})")

            for c_idx, c_data in enumerate(r_mod["chapters"], start=1):
                chap_obj = Chapter(
                    id=f"chap_{r_mod['id']}_{c_data['slug']}",
                    module_id=mod_obj.id,
                    name=c_data["name"],
                    order=c_idx,
                )
                session.add(chap_obj)
                await session.flush()

                top_obj = Topic(
                    id=f"top_{chap_obj.id}_content",
                    chapter_id=chap_obj.id,
                    name="Theory & Circuit Models",
                    content=c_data["content"],
                    content_path=None,
                    order=1,
                    question_type="reading",
                )
                session.add(top_obj)
                print(f"  -> {c_data['name']}")

        await session.commit()
        print("\n=========================================================")
        print("All learning modules successfully seeded to PostgreSQL!")
        print("=========================================================")


if __name__ == "__main__":
    asyncio.run(seed())
