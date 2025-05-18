#!/bin/bash

packages=(
  "health-secret-d6e5c0ae-2cb8-479a-b249-9b1ffcce1077"
  "health-d394e51d-07eb-4433-bc15-5e46d5e1217f"
  "es-direct-v1-72484b0e-2080-4528-a0a4-4f492451fafb"
  "es-direct-test-1d6dfd0f-1099-45a4-8d12-92a5dc703503"
  "health-3866a5e1-abe7-4611-872d-7b691dfb1007"
  "test36-ded229c1-e782-4009-a6f8-2794c985f3e4"
  "test-es-conn-2648ec5b-06ca-438c-8f2e-ed4040f2649b"
  "test35-d0cf3963-a850-4f6e-96ae-316d36cd2b68"
  "test34-c1ce8812-2260-442e-b71d-a400b5b1ad2f"
  "test33-985bc010-85e3-4f9e-bb1c-21aa98c89987"
)

for pkg in "${packages[@]}"; do
  echo "Deleting package: $pkg"
  fission pkg delete --name "$pkg"
done
