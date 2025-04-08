group "default" {
  targets = ["multiarch"]
}

target "multiarch" {
  context = "."
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64", "linux/arm64"]
  tags = [
    "readyai/bittensor-readyai-sn33:latest",
    "readyai/bittensor-readyai-sn33:v2.9.38",
  ]
  push = true
}