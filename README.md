# Task Manager — End-to-End CI/CD with Jenkins, Docker & Kubernetes

A small Flask task-manager app whose real purpose is to demonstrate a complete CI/CD pipeline:
every `git push` is automatically linted, tested, packaged as a Docker image, pushed to Docker Hub,
and rolled out to a Kubernetes cluster with zero downtime — and rolled back automatically if the deploy fails.

## Pipeline flow

```
 Developer ──git push──▶ GitHub ──poll/webhook──▶ Jenkins
                                                    │
   ┌────────────────────────────────────────────────┘
   ▼
 1. Checkout          clone repo, capture commit SHA
 2. Install deps      python venv + requirements-dev.txt
 3. Lint              flake8
 4. Unit tests        pytest + JUnit report + coverage gate (≥80%)
 5. Docker build      multi-stage image, tagged :<build#> and :latest
 6. Smoke test        run the container, hit /health
 7. Push              docker push to Docker Hub
 8. Deploy            kubectl apply (namespace, configmap, service, deployment w/ new tag)
 9. Verify            kubectl rollout status
    on failure ──▶    kubectl rollout undo (automatic rollback)
```

## Project structure

```
devops-cicd-demo/
├── app/
│   ├── app.py               Flask app (REST API + UI, /health and /ready probes)
│   └── templates/index.html UI — shows version, build # and pod name
├── tests/test_app.py        9 pytest unit tests
├── Dockerfile               multi-stage, non-root, healthcheck, gunicorn
├── Jenkinsfile              declarative pipeline (9 stages + rollback)
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── deployment.yaml      3 replicas, rolling update, probes, resource limits
│   └── service.yaml         NodePort 30080
├── jenkins/
│   ├── Dockerfile           Jenkins + docker CLI + kubectl + python
│   └── docker-compose.yml
├── scripts/
│   └── generate-kubeconfig.sh
├── requirements.txt / requirements-dev.txt
├── pytest.ini
└── README.md
```

## Prerequisites

- Docker Desktop
- minikube + kubectl
- A GitHub account (to host this repo)
- A Docker Hub account

## Setup (one time)

### 1. Push this project to GitHub
```bash
git init && git add . && git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<you>/devops-cicd-demo.git
git push -u origin main
```
Then edit `Jenkinsfile` and set `DOCKERHUB_USER` to your Docker Hub username. Commit and push.

### 2. Start Kubernetes (minikube)
```bash
minikube start --driver=docker
kubectl get nodes          # should show "minikube   Ready"
```

### 3. Start Jenkins
```bash
cd jenkins
docker compose up -d --build
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```
Open http://localhost:8080, paste the password, choose **Install suggested plugins**, and create an admin user.

### 4. Add credentials in Jenkins
*Manage Jenkins → Credentials → System → Global credentials → Add Credentials*

| ID                | Kind                    | Value |
|-------------------|-------------------------|-------|
| `dockerhub-creds` | Username with password  | Docker Hub username + an access token (Docker Hub → Account Settings → Personal access tokens) |
| `kubeconfig`      | Secret file             | the file generated below |

Generate the kubeconfig file on your machine (on Windows, run it in Git Bash or WSL):
```bash
./scripts/generate-kubeconfig.sh      # writes kubeconfig-jenkins.yaml
```
Quick check that Jenkins can reach the cluster:
```bash
docker cp kubeconfig-jenkins.yaml jenkins:/tmp/kc
docker exec jenkins kubectl --kubeconfig /tmp/kc get nodes
```

### 5. Create the pipeline job
*New Item → name `task-manager` → **Pipeline** → OK*
- **Pipeline → Definition:** Pipeline script from SCM
- **SCM:** Git → your repo URL, branch `*/main`
- **Script Path:** `Jenkinsfile`
- Save → **Build Now**

The first build runs all 9 stages. After that, Jenkins polls Git every 2 minutes and builds on every new commit.

## See it running
```bash
minikube service task-manager-service -n task-manager --url
kubectl get pods -n task-manager
```
The UI shows the build number and the pod that served the request — refresh to watch it load-balance across the 3 pods.

## Demo script (for presentation / viva)

1. Show the app at build #N.
2. Change something visible, e.g. the `<h1>` in `app/templates/index.html`, then `git commit` + `git push`.
3. Watch Jenkins pick it up and go through every stage (Stage View).
4. While it deploys: `kubectl get pods -n task-manager -w` — new pods come up before old ones terminate (zero downtime).
5. Refresh the app: the build badge now shows #N+1.
6. **Show failure handling:** break a test (e.g. change `"UP"` to `"DOWN"` in `app.py`), push — the pipeline stops at *Unit Tests* and nothing is deployed.
7. Show history: `kubectl rollout history deployment/task-manager -n task-manager`.

## Running locally (no Jenkins)
```bash
docker build -t task-manager:local .
docker run -p 5000:5000 task-manager:local
```
Then open http://localhost:5000.

## API

| Method | Path                 | Description         |
|--------|----------------------|---------------------|
| GET    | `/`                  | UI                  |
| GET    | `/health`, `/ready`  | K8s probes          |
| GET    | `/api/info`          | version, build, pod |
| GET    | `/api/tasks`         | list tasks          |
| POST   | `/api/tasks`         | `{"title": "..."}`  |
| PUT    | `/api/tasks/<id>`    | toggle done         |
| DELETE | `/api/tasks/<id>`    | delete task         |

> Tasks are stored in memory per pod — fine for a pipeline demo. A real app would add a database (e.g. PostgreSQL as a StatefulSet).

## Troubleshooting

| Problem | Fix |
|---|---|
| `permission denied ... docker.sock` | The compose file runs Jenkins as root for the demo; make sure you started it with the provided `docker-compose.yml`. |
| `network minikube not found` | Start minikube (`--driver=docker`) **before** `docker compose up`. |
| Kubectl in Jenkins times out | Re-run `generate-kubeconfig.sh` after every `minikube start` (the IP can change) and re-upload the credential. |
| `ImagePullBackOff` | Check `DOCKERHUB_USER` in the Jenkinsfile and that the image exists (and is public) on Docker Hub. |
| `rollout status` timeout | `kubectl describe pod -n task-manager <pod>` to see probe/image errors. |
