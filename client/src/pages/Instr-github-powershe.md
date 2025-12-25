git add client/src/components/LocationSearch.jsx client/src/pages/MVPIDFViewerV2.jsx
git commit -m "Use env-based Google Places key"
git push
git add client/src/pages/TestAutocomplete.jsx
git commit -m "Use env key in TestAutocomplete"
git push

git checkout bdd3bf4 -b landing-rollback-preview
M .env
Switched to a new branch 'landing-rollback-preview'
git push origin landing-rollback-preview
Total 0 (delta 0), reused 0 (delta 0), pack-reused 0 (from 0)
remote:
remote: Create a pull request for 'landing-rollback-preview' on GitHub by visiting:
remote:     https://github.com/acon560-prog/idf-web-app/pull/new/landing-rollback-preview
remote:

To https://github.com/acon560-prog/idf-web-app.git
[new branch] landing-rollback-preview → landing-rollback-preview

git add client/src/components/CTASection.jsx client/src/components/Features.jsx `
client/src/components/Hero.jsx client/src/components/Pricing.jsx

git commit -m "Add new landing page components"
git push

Enumerating objects: 13, done.
Counting objects: 100% (13/13), done.
Delta compression using up to 8 threads
Compressing objects: 100% (9/9), done.
Writing objects: 100% (9/9), 4.67 KiB | 2.33 MiB/s, done.
Total 9 (delta 4), reused 0 (delta 0), pack-reused 0 (from 0)
remote: Resolving deltas: 100% (4/4), completed with 4 local objects.
To https://github.com/acon560-prog/idf-web-app.git
45733d8..e537430 main → main

git add client/package.json client/package-lock.json client/src/index.css client/src/pages/Home.jsx client/src/pages/MVPIDFViewerV2.jsx client/src/index.css client/src/components/ui/Card.jsx client/src/components/LocationSearch.jsx lient/src/components/CTASection.jsx client/src/components/Features.jsx 

git commit -m "Update landing page and dependencies"

[main 89eb67d] Update landing page and dependencies
6 files changed, 54 insertions(+), 33 deletions(-)
create mode 100644 client/src/components/ui/Card.jsx
git push