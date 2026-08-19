#include <jni.h>

#include <ctranslate2/translator.h>

#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::mutex translator_mutex;
std::unique_ptr<ctranslate2::Translator> translator;
std::string loaded_model_path;

std::string to_string(JNIEnv* environment, jstring value) {
  const char* characters = environment->GetStringUTFChars(value, nullptr);
  if (characters == nullptr)
    throw std::runtime_error("failed to read Java string");
  std::string result(characters);
  environment->ReleaseStringUTFChars(value, characters);
  return result;
}

void throw_runtime_exception(JNIEnv* environment, const std::string& message) {
  jclass type = environment->FindClass("java/lang/RuntimeException");
  if (type != nullptr)
    environment->ThrowNew(type, message.c_str());
}

}  // namespace

extern "C" JNIEXPORT jobjectArray JNICALL
Java_cz_czechcore_app_NativeBridge_correct(
    JNIEnv* environment,
    jclass,
    jstring model_path,
    jobjectArray input_tokens) {
  try {
    const std::string path = to_string(environment, model_path);
    std::vector<std::string> tokens;
    const jsize token_count = environment->GetArrayLength(input_tokens);
    tokens.reserve(static_cast<size_t>(token_count));
    for (jsize index = 0; index < token_count; index++) {
      auto token = static_cast<jstring>(environment->GetObjectArrayElement(input_tokens, index));
      tokens.emplace_back(to_string(environment, token));
      environment->DeleteLocalRef(token);
    }

    std::lock_guard<std::mutex> lock(translator_mutex);
    if (translator == nullptr || loaded_model_path != path) {
      translator = std::make_unique<ctranslate2::Translator>(
          path,
          ctranslate2::Device::CPU,
          ctranslate2::ComputeType::FLOAT32);
      loaded_model_path = path;
    }

    ctranslate2::TranslationOptions options;
    options.beam_size = 4;
    options.num_hypotheses = 1;
    options.max_input_length = 0;
    options.max_decoding_length = 255;
    const auto results = translator->translate_batch({tokens}, options);
    if (results.empty())
      throw std::runtime_error("model returned no translation");
    const auto& output = results.front().output();

    jclass string_type = environment->FindClass("java/lang/String");
    jobjectArray result = environment->NewObjectArray(
        static_cast<jsize>(output.size()),
        string_type,
        nullptr);
    for (size_t index = 0; index < output.size(); index++) {
      jstring token = environment->NewStringUTF(output[index].c_str());
      environment->SetObjectArrayElement(result, static_cast<jsize>(index), token);
      environment->DeleteLocalRef(token);
    }
    return result;
  } catch (const std::exception& error) {
    throw_runtime_exception(environment, error.what());
    return nullptr;
  }
}
