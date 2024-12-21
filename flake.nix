{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    rust-overlay.url = "github:oxalica/rust-overlay";
    rust-overlay.inputs.nixpkgs.follows = "nixpkgs";

    pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
    pyproject-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    rust-overlay,
    pyproject-nix,
  } @ inputs:
    flake-utils.lib.eachDefaultSystem
    (
      system: let
        overlays = [(import rust-overlay)];
        pkgs = import nixpkgs {inherit system overlays;};
        lib = pkgs.lib;

        project = pyproject-nix.lib.project.loadPyproject {projectRoot = ./.;};

        python = pkgs.python3.override {
          self = python;
          packageOverrides = pyfinal: pyprev: {
            pydantic-settings = pyprev.pydantic-settings.overridePythonAttrs (old: rec {
              version = "2.6.1";
              src = pkgs.fetchPypi {
                pname = "pydantic_settings";
                inherit version;
                hash = "sha256-4PklRtipkjy4lBaJq/hdZgGowZoj6Xo0spZKLj+BPKA=";
              };
            });

            typer-slim = pyprev.typer.overridePythonAttrs (old: rec {
              pname = "typer-slim";
              version = "0.12.5";

              src = pkgs.fetchPypi {
                pname = "typer_slim";
                inherit version;
                hash = "sha256-yOP8+TzH3VhANt+HVdLiNj+F+KTdAox5Ee7T8Azw67E=";
              };
            });
          };
        };
        rust = pkgs.rust-bin.stable.latest.default;
        rustPlatform = pkgs.makeRustPlatform {
          rustc = rust;
          cargo = rust;
        };
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [alejandra maturin rust python];

          shellHook = ''
            export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib.outPath}/lib:${pkgs.pythonManylinuxPackages.manylinux2014Package}/lib:$LD_LIBRARY_PATH";
            test -d .nix-venv || ${python.interpreter} -m venv .nix-venv
            source .nix-venv/bin/activate
          '';
        };

        packages.default = let
          projectConfig = project.renderers.buildPythonPackage {inherit python;};
        in
          python.pkgs.buildPythonApplication rec {
            name = "wakapi-anyide-${version}";
            version = "0.6.8";
            pyproject = true;

            cargoDeps = rustPlatform.fetchCargoTarball {
              inherit src;
              hash = "sha256-qSU1QkYeGrVqWo+H+nB0DziJTjagaPczQhONV6ZFX14=";
            };

            nativeBuildInputs = with pkgs; [
              maturin
              rustPlatform.cargoSetupHook
              rustPlatform.maturinBuildHook
            ];

            inherit (projectConfig) dependencies;

            src = ./.;
          };
      }
    );
}
