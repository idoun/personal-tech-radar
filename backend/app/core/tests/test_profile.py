from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.profile import DEFAULT_TECH_RADAR_PROFILE, load_tech_radar_profile


def test_load_profile_from_yaml(tmp_path: Path):
    profile_path = tmp_path / 'profile.yaml'
    profile_path.write_text(
        '''
profile:
  interests:
    - Test Interest
  projects:
    - name: Test Project
      description: Example project
      keywords:
        - alpha
        - beta
'''.strip()
        + '\n',
        encoding='utf-8',
    )

    profile = load_tech_radar_profile(str(profile_path))

    assert profile.interests == ['Test Interest']
    assert len(profile.projects) == 1
    assert profile.projects[0].name == 'Test Project'
    assert profile.projects[0].keywords == ['alpha', 'beta']


def test_missing_profile_uses_default(tmp_path: Path):
    profile = load_tech_radar_profile(str(tmp_path / 'missing.yaml'))

    assert profile.model_dump() == DEFAULT_TECH_RADAR_PROFILE.model_dump()


def test_invalid_profile_uses_default(tmp_path: Path):
    profile_path = tmp_path / 'broken.yaml'
    profile_path.write_text('profile: [not-valid', encoding='utf-8')

    profile = load_tech_radar_profile(str(profile_path))

    assert profile.model_dump() == DEFAULT_TECH_RADAR_PROFILE.model_dump()
