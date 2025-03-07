  using UnityEngine;
  using UnityEditor;
  using UnityEditor.Animations;
  using System.Collections.Generic;
  using System.Linq;
  using System.IO;

  public class DigglesAnimationSetup : EditorWindow
  {
      private GameObject targetModel;
      private float frameRate = 12f;
      private int transitionDuration = 1;
      private bool standardizeFrameNames = true;

      [MenuItem("Tools/Setup Animator")]
      public static void ShowWindow()
      {
          GetWindow<DigglesAnimationSetup>("Diggles Animation Setup");
      }

      private void OnGUI()
      {
          GUILayout.Label("Diggles Model Animation Setup", EditorStyles.boldLabel);

          EditorGUILayout.Space();
          targetModel = EditorGUILayout.ObjectField("Model", targetModel, typeof(GameObject), true) as GameObject;
          frameRate = EditorGUILayout.FloatField("Frame Rate", frameRate);
          transitionDuration = EditorGUILayout.IntField("Transition Duration (frames)", transitionDuration);
          standardizeFrameNames = EditorGUILayout.Toggle("Standardize Frame Names", standardizeFrameNames);

          EditorGUILayout.Space();
          EditorGUILayout.HelpBox("1. Select your imported Diggles model\n2. Click 'Setup Animator' to create animations", MessageType.Info);

          GUI.enabled = targetModel != null;
          if (GUILayout.Button("Setup Animator"))
          {
              SetupAnimator();
          }
          GUI.enabled = true;
      }

      private void SetupAnimator()
      {
          if (targetModel == null)
          {
              EditorUtility.DisplayDialog("Error", "Please select a model first!", "OK");
              return;
          }

          // Проверяем структуру модели
          Transform root = targetModel.transform;
          Transform[] animationContainers = root.Cast<Transform>().ToArray();

          if (animationContainers.Length == 0)
          {
              EditorUtility.DisplayDialog("Error", "The selected model doesn't have the expected structure. No animation containers found.",
  "OK");
              return;
          }

          // Стандартизируем имена фреймов если выбрана опция
          if (standardizeFrameNames)
          {
              StandardizeFrameNames(root);
          }

          // Создаем папку для сохранения анимаций и контроллера
          string modelName = targetModel.name;
          string assetsPath = "Assets/Animations/" + modelName;
          if (!Directory.Exists(assetsPath))
          {
              Directory.CreateDirectory(assetsPath);
          }

          // Создаем контроллер аниматора
          string controllerPath = assetsPath + "/" + modelName + "Controller.controller";
          AnimatorController controller = AnimatorController.CreateAnimatorControllerAtPath(controllerPath);

          // Добавляем параметр для переключения анимаций
          controller.AddParameter("AnimationIndex", AnimatorControllerParameterType.Int);

          // Создаем слой по умолчанию
          AnimatorControllerLayer baseLayer = controller.layers[0];
          baseLayer.name = "Base Layer";

          // Список для хранения информации о всех кадрах модели
          Dictionary<Transform, List<Transform>> allAnimFrames = new Dictionary<Transform, List<Transform>>();

          // Сначала - устанавливаем исходные состояния объектов в сцене
          // По умолчанию, все анимации, кроме первой, отключены
          for (int i = 0; i < animationContainers.Length; i++)
          {
              Transform animContainer = animationContainers[i];
              bool isActive = (i == 0); // Первая анимация активна, остальные неактивны
              animContainer.gameObject.SetActive(isActive);

              // Все кадры по умолчанию отключены
              foreach (Transform child in animContainer)
              {
                  if (child.name.StartsWith("frame_"))
                  {
                      child.gameObject.SetActive(false);
                  }
              }
          }

          // Теперь - активируем первый кадр первой анимации
          bool firstFrameActivated = false;
          if (animationContainers.Length > 0)
          {
              Transform firstAnim = animationContainers[0];
              Transform firstFrame = null;

              // Ищем первый кадр
              foreach (Transform child in firstAnim)
              {
                  if (child.name.StartsWith("frame_"))
                  {
                      firstFrame = child;
                      break;
                  }
              }

              // Активируем первый кадр
              if (firstFrame != null)
              {
                  firstFrame.gameObject.SetActive(true);
                  firstFrameActivated = true;
                  Debug.Log($"Activated first frame: {firstFrame.name} of animation: {firstAnim.name}");
              }
          }

          // Теперь собираем все кадры для всех анимаций
          foreach (Transform animContainer in animationContainers)
          {
              List<Transform> frames = new List<Transform>();
              foreach (Transform child in animContainer)
              {
                  if (child.name.StartsWith("frame_"))
                  {
                      frames.Add(child);
                  }
              }

              // Сортируем кадры по номеру
              frames = frames.OrderBy(f => {
                  string frameName = f.name.Replace("frame_", "");
                  int frameNum;
                  int.TryParse(frameName, out frameNum);
                  return frameNum;
              }).ToList();

              if (frames.Count > 0)
              {
                  allAnimFrames.Add(animContainer, frames);
                  Debug.Log($"Animation '{animContainer.name}' has {frames.Count} frames.");
              }
              else
              {
                  Debug.LogWarning($"Animation '{animContainer.name}' has no frames!");
              }
          }

          // Для каждого контейнера анимации создаем анимационный клип
          foreach (var animEntry in allAnimFrames)
          {
              Transform animContainer = animEntry.Key;
              List<Transform> frames = animEntry.Value;

              // Создаем анимационный клип
              string animationName = animContainer.name;
              string clipPath = assetsPath + "/" + modelName + "_" + animationName + ".anim";

              // Создаем новый анимационный клип
              AnimationClip clip = new AnimationClip();
              clip.name = animationName;
              clip.frameRate = frameRate;
              clip.wrapMode = WrapMode.Loop;

              // Для каждого кадра этой анимации настраиваем видимость
              float timePerFrame = 1.0f / frameRate;
              float totalTime = frames.Count * timePerFrame;

              // Сначала настраиваем видимость корней анимаций
              foreach (var otherAnimEntry in allAnimFrames)
              {
                  Transform otherAnim = otherAnimEntry.Key;
                  string otherAnimPath = GetRelativePath(otherAnim, targetModel.transform);

                  // Активируем только текущую анимацию
                  bool isThisAnim = (otherAnim == animContainer);

                  // Настраиваем видимость корня анимации
                  AnimationCurve animCurve = new AnimationCurve();
                  animCurve.AddKey(new Keyframe(0, isThisAnim ? 1 : 0));
                  animCurve.AddKey(new Keyframe(totalTime, isThisAnim ? 1 : 0));
                  clip.SetCurve(otherAnimPath, typeof(GameObject), "m_IsActive", animCurve);
              }

              // Для кадров текущей анимации настраиваем покадровую видимость
              for (int i = 0; i < frames.Count; i++)
              {
                  Transform frame = frames[i];
                  string framePath = GetRelativePath(frame, targetModel.transform);

                  // Для каждого кадра создаем кривую видимости
                  AnimationCurve frameCurve = new AnimationCurve();

                  // ВАЖНО! Сначала определим, что происходит в самом начале - первый кадр включен, остальные выключены
                  if (i == 0)
                  {
                      // Первый кадр включен в начале
                      frameCurve.AddKey(new Keyframe(0, 1));
                  }
                  else
                  {
                      // Все остальные кадры выключены в начале
                      frameCurve.AddKey(new Keyframe(0, 0));
                  }

                  // Устанавливаем корректные ключевые точки анимации для этого кадра
                  for (int j = 0; j < frames.Count; j++)
                  {
                      float startTime = j * timePerFrame;
                      float endTime = (j + 1) * timePerFrame;

                      if (endTime > totalTime) endTime = totalTime;

                      // Добавляем ключевые точки только если это важно для текущего кадра
                      if (j == i - 1 || j == i || j == i + 1)
                      {
                          // Если это переход на текущий кадр
                          if (j == i)
                          {
                              // Точка непосредственно перед включением
                              if (startTime > 0)
                              {
                                  frameCurve.AddKey(new Keyframe(startTime - 0.0001f, 0));
                              }

                              // Точка включения
                              frameCurve.AddKey(new Keyframe(startTime, 1));

                              // Точка перед выключением
                              frameCurve.AddKey(new Keyframe(endTime - 0.0001f, 1));
                          }
                          // Если это переход к следующему кадру (выключение текущего)
                          else if (j == i)
                          {
                              // Точка выключения (конец текущего кадра)
                              frameCurve.AddKey(new Keyframe(endTime, 0));
                          }
                      }
                  }

                  // Для всех кадров, кроме последнего, добавляем точку выключения
                  if (i < frames.Count - 1)
                  {
                      float endTime = (i + 1) * timePerFrame;
                      frameCurve.AddKey(new Keyframe(endTime, 0));
                  }

                  // Последний кадр остается включенным до самого конца, затем выключается и цикл повторяется
                  if (i == frames.Count - 1)
                  {
                      frameCurve.AddKey(new Keyframe(totalTime - 0.0001f, 1));
                      frameCurve.AddKey(new Keyframe(totalTime, 0));
                  }

                  // Устанавливаем кривую для этого кадра
                  clip.SetCurve(framePath, typeof(GameObject), "m_IsActive", frameCurve);
              }

              // Принудительно устанавливаем все кривые как константные
              SetConstantCurves(clip);

              // Сохраняем клип как актив
              AssetDatabase.CreateAsset(clip, clipPath);

              // Добавляем состояние в контроллер
              AnimatorState state = baseLayer.stateMachine.AddState(animationName);
              state.motion = clip;
              state.writeDefaultValues = true;

              // Добавляем правило перехода в это состояние
              AnimatorStateTransition transition = baseLayer.stateMachine.AddAnyStateTransition(state);
              transition.duration = transitionDuration / frameRate; // Конвертируем кадры в секунды
              transition.hasExitTime = false;
              transition.canTransitionToSelf = false;

              int animIndex = animationContainers.ToList().IndexOf(animContainer);
              transition.AddCondition(AnimatorConditionMode.Equals, animIndex, "AnimationIndex");
          }

          // Настраиваем компонент аниматора на модели
          Animator animator = targetModel.GetComponent<Animator>();
          if (animator == null)
          {
              animator = targetModel.AddComponent<Animator>();
          }
          animator.runtimeAnimatorController = controller;

          AssetDatabase.SaveAssets();
          AssetDatabase.Refresh();

          // Выводим информацию о том, как использовать аниматор
          EditorUtility.DisplayDialog("Success",
              $"Created {allAnimFrames.Count} animations and animator controller.\n\n" +
              $"• First animation is active by default\n" +
              $"• Change the 'AnimationIndex' parameter to switch animations\n\n" +
              $"Example:\n" +
              $"GetComponent<Animator>().SetInteger(\"AnimationIndex\", 1);", "OK");
      }

      // Получаем относительный путь трансформа для использования в анимации
      private string GetRelativePath(Transform transform, Transform root)
      {
          if (transform == root) return "";

          if (transform.parent == root)
              return transform.name;
          else
              return GetRelativePath(transform.parent, root) + "/" + transform.name;
      }

      // Устанавливает все кривые в клипе как константные
      private void SetConstantCurves(AnimationClip clip)
      {
          AnimationUtility.SetAnimationClipSettings(clip, new AnimationClipSettings { loopTime = true });

          EditorCurveBinding[] bindings = AnimationUtility.GetCurveBindings(clip);
          foreach (var binding in bindings)
          {
              AnimationCurve curve = AnimationUtility.GetEditorCurve(clip, binding);
              for (int i = 0; i < curve.keys.Length; i++)
              {
                  var key = curve.keys[i];
                  key.inTangent = float.PositiveInfinity;
                  key.outTangent = float.PositiveInfinity;
                  curve.MoveKey(i, key);
              }
              AnimationUtility.SetEditorCurve(clip, binding, curve);
          }
      }

      // Стандартизирует имена фреймов в числовом формате (frame_000, frame_001, и т.д.)
      private void StandardizeFrameNames(Transform root)
      {
          bool renamed = false;

          foreach (Transform animContainer in root)
          {
              List<Transform> frames = new List<Transform>();

              // Собираем все фреймы
              foreach (Transform child in animContainer)
              {
                  if (child.name.StartsWith("frame_"))
                  {
                      frames.Add(child);
                  }
              }

              // Если нет фреймов, пропускаем
              if (frames.Count == 0) continue;

              // Сортируем фреймы по текущему имени
              frames = frames.OrderBy(f => {
                  string frameName = f.name.Replace("frame_", "");

                  // Попробуем как целое число
                  int frameNum;
                  if (int.TryParse(frameName, out frameNum))
                      return frameNum;

                  // Если не получилось, попробуем как число с плавающей точкой
                  float frameFloat;
                  if (float.TryParse(frameName, out frameFloat))
                      return (int)(frameFloat * 100);

                  // Если совсем не получилось, вернем 0
                  return 0;
              }).ToList();

              // Переименовываем фреймы в последовательном порядке
              for (int i = 0; i < frames.Count; i++)
              {
                  string newName = $"frame_{i:000}";
                  if (frames[i].name != newName)
                  {
                      frames[i].name = newName;
                      renamed = true;
                  }
              }
          }

          if (renamed)
          {
              Debug.Log("Frame names have been standardized.");
          }
      }
  }