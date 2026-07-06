.PHONY: verify pack-zip pack-smoke setup eval clean

verify:
	./scripts/verify-pack.sh

pack-zip:
	./scripts/build-pack-zip.sh

pack-smoke:
	./scripts/pack-smoke.sh

setup:
	./scripts/setup-cad-sidecar.sh

eval:
	./scripts/eval-cad-models.sh

clean:
	rm -rf dist
