upload:
	./scripts/release.sh


obfuscate:
	uv run pyarmor gen -O ./build/obf -r ./tolov