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

        # If we don't do this, the renderers and validators will use the old project attrset
        updateProjectMethods = let
          inherit (pyproject-nix.lib) renderers validators;
          curryProject = attrs: project:
            lib.mapAttrs (
              _: func: args:
                func (args // {inherit project;})
            )
            attrs;
        in
          project:
            (lib.makeExtensible (final: project)).extend (
              final: prev: {
                # Set renderers/validators to use new project deps
                renderers = curryProject renderers final;
                validators = curryProject validators final;
              }
            );

        # We need to remove the "maturin" dependency because it is installed via nix, and not in the python packages
        removeMaturinDeps = project: let
          filteredDeps = lib.mapAttrs (name: value:
            if lib.elem name ["dependencies" "build-systems"]
            then lib.filter (dep: dep.name != "maturin") value
            else value)
          project.dependencies;

          project' = lib.setAttr project "dependencies" filteredDeps;
        in
          updateProjectMethods project';

        pyproject = removeMaturinDeps (pyproject-nix.lib.project.loadPyproject {projectRoot = ./.;});

        rust = pkgs.rust-bin.stable.latest.default;
        rustPlatform = pkgs.makeRustPlatform {
          rustc = rust;
          cargo = rust;
        };

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
      in {
        # Setup a shell for direnv and `nix shell`
        devShells.default = let
          projectPackages = pyproject.renderers.withPackages {inherit python;};

          pythonEnv = python.withPackages projectPackages;

          libPath = lib.makeLibraryPath (with pkgs; [
            stdenv.cc.cc
          ]);
        in
          pkgs.mkShell {
            nativeBuildInputs = with pkgs; [alejandra maturin rust pythonEnv];

            shellHook = ''
              export "LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${libPath}"
              VENV=.nix-venv

              if test ! -d $VENV; then
                python3.12 -m venv $VENV
              fi

              source ./$VENV/bin/activate
              export PYTHONPATH=`pwd`/$VENV/${python.sitePackages}/:$PYTHONPATH
            '';
          };

        # Package the wakapi-anyide to be used as a package and for `nix run`
        packages.default = let
          projectConfig = pyproject.renderers.buildPythonPackage {
            inherit python;
          };
        in
          python.pkgs.buildPythonApplication (projectConfig
            // {
              cargoDeps = rustPlatform.fetchCargoTarball {
                src = projectConfig.src;
                hash = "sha256-qSU1QkYeGrVqWo+H+nB0DziJTjagaPczQhONV6ZFX14=";
              };

              nativeBuildInputs = with pkgs; [
                maturin
                rustPlatform.cargoSetupHook
                rustPlatform.maturinBuildHook
              ];
            });
      }
    );
}
