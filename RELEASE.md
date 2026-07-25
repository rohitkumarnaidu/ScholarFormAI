# Release Process

## Versioning

We follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible feature additions
- **PATCH**: Backward-compatible bug fixes

## Release Checklist

### Preparation

- [ ] All tests pass: `make test`
- [ ] Linting passes: `make lint`
- [ ] Documentation is up to date
- [ ] CHANGELOG.md is updated
- [ ] Version numbers updated in all packages
- [ ] Release branch created: `release/vX.Y.Z`

### Release Steps

1. **Create release branch**
   ```bash
   git checkout -b release/v1.2.3
   ```

2. **Update version numbers**
   - `backend/app/__init__.py`
   - `cli/amf/__init__.py`
   - `sdk/amf_sdk/__init__.py`
   - `frontend/package.json`

3. **Update CHANGELOG.md**
   - Move "Unreleased" changes to new version

4. **Create pull request**
   - Title: `chore: release v1.2.3`
   - Get maintainer review

5. **Tag and release**
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

6. **Build and publish**
   ```bash
   # Build Python packages
   cd backend && python setup.py sdist bdist_wheel
   cd cli && python setup.py sdist bdist_wheel
   cd sdk && python setup.py sdist bdist_wheel

   # Publish to PyPI
   twine upload dist/*

   # Build and push Docker images
   docker compose build
   docker tag amf-backend:latest ghcr.io/amf/backend:v1.2.3
   docker push ghcr.io/amf/backend:v1.2.3
   ```

7. **Create GitHub Release**
   - Title: `v1.2.3`
   - Description: Summary from CHANGELOG
   - Attach build artifacts

### Post-Release

- [ ] Merge release branch into main
- [ ] Merge main into develop
- [ ] Update documentation site
- [ ] Announce release on community channels

## Hotfix Process

1. Create branch from tag: `git checkout -b hotfix/v1.2.4 v1.2.3`
2. Apply fix
3. Bump patch version
4. Follow release steps from step 3

## Automated Releases

GitHub Actions automates:
- Running tests on all PRs
- Building Docker images on tag pushes
- Publishing to PyPI on release creation
- Deploying documentation site on main branch pushes
